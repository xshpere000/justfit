// Package v2 提供新版本的服务层，使用 DTO 模式
package v2

import (
	"context"

	"justfit/internal/appdir"
	apperrors "justfit/internal/errors"
	"justfit/internal/connector"
	"justfit/internal/dto/mapper"
	"justfit/internal/dto/request"
	"justfit/internal/dto/response"
	"justfit/internal/logger"
	"justfit/internal/security"
	"justfit/internal/storage"
)

// ConnectionService 连接服务
type ConnectionService struct {
	ctx           context.Context
	repos         *storage.Repositories
	connMgr       *connector.ConnectorManager
	credentialMgr *security.CredentialManager
	mapper        *mapper.ConnectionMapper
	log           logger.Logger
}

// NewConnectionService 创建连接服务
func NewConnectionService(
	ctx context.Context,
	repos *storage.Repositories,
	connMgr *connector.ConnectorManager,
	credentialMgr *security.CredentialManager,
) *ConnectionService {
	return &ConnectionService{
		ctx:           ctx,
		repos:         repos,
		connMgr:       connMgr,
		credentialMgr: credentialMgr,
		mapper:        mapper.NewConnectionMapper(),
		log:           logger.With(logger.Str("service", "connection")),
	}
}

// List 获取连接列表
func (s *ConnectionService) List() ([]response.ConnectionListItem, error) {
	s.log.Debug("获取连接列表")

	conns, err := s.repos.Connection.List()
	if err != nil {
		s.log.Error("获取连接列表失败", logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "获取连接列表失败")
	}

	result := make([]response.ConnectionListItem, len(conns))
	for i, c := range conns {
		// 获取 VM 数量
		vmCount, _ := s.repos.VM.CountByConnectionID(c.ID)
		result[i] = *s.mapper.ToListItem(&c, vmCount)
	}

	s.log.Info("获取连接列表成功", logger.Int("count", len(result)))
	return result, nil
}

// GetByID 获取单个连接
func (s *ConnectionService) GetByID(id uint) (*response.ConnectionResponse, error) {
	s.log.Debug("获取连接", logger.Uint("id", id))

	conn, err := s.repos.Connection.GetByID(id)
	if err != nil {
		s.log.Error("获取连接失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrConnectionNotFound
	}

	return s.mapper.ToDTO(conn), nil
}

// Create 创建连接
func (s *ConnectionService) Create(req *request.CreateConnectionRequest) (uint, error) {
	s.log.Info("创建连接", logger.String("name", req.Name), logger.String("platform", req.Platform))

	if s.credentialMgr == nil {
		s.log.Error("凭据管理器未初始化")
		return 0, apperrors.ErrInternalError.WithMessage("安全服务未初始化，无法安全保存凭据")
	}

	conn := &storage.Connection{
		Name:     req.Name,
		Platform: req.Platform,
		Host:     req.Host,
		Port:     req.Port,
		Username: req.Username,
		Password: "", // 数据库不存储明文密码
		Insecure: req.Insecure,
		Status:   "disconnected",
	}

	// 创建连接记录
	if err := s.repos.Connection.Create(conn); err != nil {
		s.log.Error("创建连接失败", logger.Err(err))
		return 0, apperrors.ErrInternalError.Wrap(err, "创建连接失败")
	}

	// 保存到凭据管理器（加密）
	connForEncryption := *conn
	connForEncryption.Password = req.Password
	if err := s.credentialMgr.SaveConnection(&connForEncryption); err != nil {
		s.log.Error("保存凭据失败", logger.Uint("id", conn.ID), logger.Err(err))
		s.repos.Connection.Delete(conn.ID)
		return 0, apperrors.ErrInternalError.Wrap(err, "保存凭据失败")
	}

	s.log.Info("创建连接成功", logger.Uint("id", conn.ID))
	return conn.ID, nil
}

// Update 更新连接
func (s *ConnectionService) Update(req *request.UpdateConnectionRequest) error {
	s.log.Info("更新连接", logger.Uint("id", req.ID))

	conn, err := s.repos.Connection.GetByID(req.ID)
	if err != nil {
		s.log.Error("获取连接失败", logger.Uint("id", req.ID), logger.Err(err))
		return apperrors.ErrConnectionNotFound
	}

	// 更新字段
	conn.Name = req.Name
	conn.Platform = req.Platform
	conn.Host = req.Host
	conn.Port = req.Port
	conn.Username = req.Username
	conn.Insecure = req.Insecure

	// 如果提供了新密码，更新凭据
	if req.Password != "" && s.credentialMgr != nil {
		conn.Password = req.Password // 临时设置用于加密
		if err := s.credentialMgr.SaveConnection(conn); err != nil {
			s.log.Error("更新凭据失败", logger.Uint("id", req.ID), logger.Err(err))
			return apperrors.ErrInternalError.Wrap(err, "更新凭据失败")
		}
		conn.Password = "" // 清除明文
	}

	// 更新数据库
	if err := s.repos.Connection.Update(conn); err != nil {
		s.log.Error("更新连接失败", logger.Uint("id", req.ID), logger.Err(err))
		return apperrors.ErrInternalError.Wrap(err, "更新连接失败")
	}

	// 移除内存中的连接缓存
	s.connMgr.Remove(req.ID)

	s.log.Info("更新连接成功", logger.Uint("id", req.ID))
	return nil
}

// Delete 删除连接
func (s *ConnectionService) Delete(id uint) error {
	s.log.Info("删除连接", logger.Uint("id", id))

	s.connMgr.Remove(id)

	if err := s.repos.Connection.Delete(id); err != nil {
		s.log.Error("删除连接失败", logger.Uint("id", id), logger.Err(err))
		return apperrors.ErrInternalError.Wrap(err, "删除连接失败")
	}

	s.log.Info("删除连接成功", logger.Uint("id", id))
	return nil
}

// Test 测试连接
func (s *ConnectionService) Test(id uint) (*response.TestConnectionResponse, error) {
	s.log.Info("测试连接", logger.Uint("id", id))

	conn, err := s.repos.Connection.GetByID(id)
	if err != nil {
		s.log.Error("获取连接失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrConnectionNotFound
	}

	// 从凭据管理器加载密码
	if s.credentialMgr != nil {
		if err := s.credentialMgr.LoadConnection(conn); err != nil {
			s.log.Error("加载凭据失败", logger.Uint("id", id), logger.Err(err))
			return nil, apperrors.ErrInternalError.Wrap(err, "加载凭据失败")
		}
	}

	config := &connector.ConnectionConfig{
		ID:       conn.ID,
		Name:     conn.Name,
		Platform: connector.PlatformType(conn.Platform),
		Host:     conn.Host,
		Port:     conn.Port,
		Username: conn.Username,
		Password: conn.Password,
		Insecure: conn.Insecure,
	}

	client, err := connector.NewConnector(config)
	if err != nil {
		s.repos.Connection.UpdateStatus(id, "error")
		s.log.Error("创建连接失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrInternalError.Wrap(err, "创建连接失败")
	}
	defer client.Close()

	if err := client.TestConnection(); err != nil {
		s.repos.Connection.UpdateStatus(id, "error")
		s.log.Error("连接测试失败", logger.Uint("id", id), logger.Err(err))
		return nil, apperrors.ErrConnectionTestFailed.Wrap(err, "连接测试失败")
	}

	s.repos.Connection.UpdateStatus(id, "connected")
	s.log.Info("连接测试成功", logger.Uint("id", id))

	return &response.TestConnectionResponse{
		Success: true,
		Message: "连接成功",
	}, nil
}

// GetLogsDir 获取日志目录
func (s *ConnectionService) GetLogsDir() (string, error) {
	return appdir.GetLogDir()
}
