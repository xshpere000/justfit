// Package task 提供任务调度和执行功能
package task

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// TaskStatus 任务状态
type TaskStatus string

const (
	StatusPending   TaskStatus = "pending"
	StatusRunning   TaskStatus = "running"
	StatusCompleted TaskStatus = "completed"
	StatusFailed    TaskStatus = "failed"
	StatusCancelled TaskStatus = "cancelled"
)

// TaskType 任务类型
type TaskType string

const (
	TypeCollection  TaskType = "collection"  // 数据采集
	TypeAnalysis    TaskType = "analysis"    // 分析任务
	TypeReport      TaskType = "report"      // 报告生成
	TypeSync        TaskType = "sync"        // 数据同步
)

// Task 任务定义
type Task struct {
	ID          uint                   `json:"id"`
	Type        TaskType               `json:"type"`
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Status      TaskStatus             `json:"status"`
	Progress    float64                `json:"progress"`
	Config      map[string]interface{} `json:"config"`
	Error       string                 `json:"error,omitempty"`
	CreatedAt   time.Time              `json:"created_at"`
	StartedAt   *time.Time             `json:"started_at,omitempty"`
	CompletedAt *time.Time             `json:"completed_at,omitempty"`
}

// TaskResult 任务执行结果
type TaskResult struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data,omitempty"`
}

// TaskFunc 任务执行函数
type TaskFunc func(ctx context.Context, task *Task, progressCh chan<- float64) (*TaskResult, error)

// Executor 任务执行器接口
type Executor interface {
	Execute(ctx context.Context, task *Task, progressCh chan<- float64) (*TaskResult, error)
}

// Scheduler 任务调度器
type Scheduler struct {
	mu           sync.RWMutex
	tasks        map[uint]*Task
	executors    map[TaskType]Executor
	workerPool   chan struct{}
	progressSubs map[uint][]chan float64
	resultSubs   map[uint][]chan *TaskResult
	taskCounter  uint
	running      bool
}

// NewScheduler 创建任务调度器
func NewScheduler(workerCount int) *Scheduler {
	if workerCount <= 0 {
		workerCount = 3
	}

	return &Scheduler{
		tasks:        make(map[uint]*Task),
		executors:    make(map[TaskType]Executor),
		workerPool:   make(chan struct{}, workerCount),
		progressSubs: make(map[uint][]chan float64),
		resultSubs:   make(map[uint][]chan *TaskResult),
		taskCounter:  0,
		running:      true,
	}
}

// RegisterExecutor 注册任务执行器
func (s *Scheduler) RegisterExecutor(taskType TaskType, executor Executor) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.executors[taskType] = executor
}

// Create 创建新任务
func (s *Scheduler) Create(taskType TaskType, name string, config map[string]interface{}) (*Task, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.running {
		return nil, fmt.Errorf("调度器已关闭")
	}

	s.taskCounter++
	task := &Task{
		ID:          s.taskCounter,
		Type:        taskType,
		Name:        name,
		Description: name,
		Status:      StatusPending,
		Progress:    0,
		Config:      config,
		CreatedAt:   time.Now(),
	}

	s.tasks[task.ID] = task
	return task, nil
}

// Submit 提交任务执行
func (s *Scheduler) Submit(ctx context.Context, taskID uint) error {
	s.mu.Lock()
	task, exists := s.tasks[taskID]
	if !exists {
		s.mu.Unlock()
		return fmt.Errorf("任务不存在: %d", taskID)
	}

	if task.Status != StatusPending {
		s.mu.Unlock()
		return fmt.Errorf("任务状态错误: %s", task.Status)
	}

	// 获取 worker
	select {
	case s.workerPool <- struct{}{}:
		// 获取成功
	default:
		s.mu.Unlock()
		return fmt.Errorf("任务队列已满，请稍后重试")
	}

	// 更新任务状态
	task.Status = StatusRunning
	now := time.Now()
	task.StartedAt = &now
	s.mu.Unlock()

	// 异步执行
	go s.execute(ctx, task)

	return nil
}

// execute 执行任务
func (s *Scheduler) execute(ctx context.Context, task *Task) {
	defer func() {
		<-s.workerPool // 释放 worker
	}()

	// 获取执行器
	s.mu.RLock()
	executor, exists := s.executors[task.Type]
	s.mu.RUnlock()

	if !exists {
		s.completeTask(task, &TaskResult{
			Success: false,
			Message: fmt.Sprintf("未找到 %s 类型的执行器", task.Type),
		}, fmt.Errorf("未找到执行器"))
		return
	}

	// 创建进度通道
	progressCh := make(chan float64, 10)
	defer close(progressCh)

	// 启动进度广播
	go s.broadcastProgress(task.ID, progressCh)

	// 执行任务
	result, err := executor.Execute(ctx, task, progressCh)
	if err != nil {
		s.completeTask(task, &TaskResult{
			Success: false,
			Message: err.Error(),
		}, err)
		return
	}

	s.completeTask(task, result, nil)
}

// completeTask 完成任务
func (s *Scheduler) completeTask(task *Task, result *TaskResult, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err != nil {
		task.Status = StatusFailed
		task.Error = err.Error()
	} else if result.Success {
		task.Status = StatusCompleted
	} else {
		task.Status = StatusFailed
		task.Error = result.Message
	}

	now := time.Now()
	task.CompletedAt = &now
	task.Progress = 100

	// 通知结果订阅者
	if subs, exists := s.resultSubs[task.ID]; exists {
		for _, ch := range subs {
			select {
			case ch <- result:
			default:
			}
		}
		delete(s.resultSubs, task.ID)
	}

	// 清理进度订阅
	delete(s.progressSubs, task.ID)
}

// broadcastProgress 广播进度
func (s *Scheduler) broadcastProgress(taskID uint, progressCh <-chan float64) {
	for progress := range progressCh {
		s.mu.Lock()
		if task, exists := s.tasks[taskID]; exists {
			task.Progress = progress
		}
		s.mu.Unlock()

		// 通知订阅者
		s.mu.RLock()
		if subs, exists := s.progressSubs[taskID]; exists {
			for _, ch := range subs {
				select {
				case ch <- progress:
				default:
				}
			}
		}
		s.mu.RUnlock()
	}
}

// Get 获取任务
func (s *Scheduler) Get(taskID uint) (*Task, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	task, exists := s.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("任务不存在: %d", taskID)
	}

	// 返回副本
	taskCopy := *task
	return &taskCopy, nil
}

// List 列出任务
func (s *Scheduler) List(status TaskStatus, limit, offset int) ([]*Task, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// 先收集符合条件的任务
	var matched []*Task
	for _, task := range s.tasks {
		if status != "" && task.Status != status {
			continue
		}
		// 返回副本
		taskCopy := *task
		matched = append(matched, &taskCopy)
	}

	// 按 ID 排序以确保顺序稳定
	sortTasks(matched)

	// 应用 offset 和 limit
	start := offset
	if start > len(matched) {
		start = len(matched)
	}

	end := start + limit
	if limit <= 0 || end > len(matched) {
		end = len(matched)
	}

	return matched[start:end], nil
}

// sortTasks 按 ID 排序任务
func sortTasks(tasks []*Task) {
	for i := 0; i < len(tasks); i++ {
		for j := i + 1; j < len(tasks); j++ {
			if tasks[i].ID > tasks[j].ID {
				tasks[i], tasks[j] = tasks[j], tasks[i]
			}
		}
	}
}

// Cancel 取消任务
func (s *Scheduler) Cancel(taskID uint) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	task, exists := s.tasks[taskID]
	if !exists {
		return fmt.Errorf("任务不存在: %d", taskID)
	}

	if task.Status != StatusPending && task.Status != StatusRunning {
		return fmt.Errorf("任务无法取消，当前状态: %s", task.Status)
	}

	task.Status = StatusCancelled
	now := time.Now()
	task.CompletedAt = &now

	// 通知结果订阅者
	result := &TaskResult{
		Success: false,
		Message: "任务已取消",
	}
	if subs, exists := s.resultSubs[taskID]; exists {
		for _, ch := range subs {
			select {
			case ch <- result:
			default:
			}
		}
		delete(s.resultSubs, taskID)
	}

	return nil
}

// SubscribeProgress 订阅任务进度
func (s *Scheduler) SubscribeProgress(taskID uint) (<-chan float64, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	task, exists := s.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("任务不存在: %d", taskID)
	}

	ch := make(chan float64, 10)
	s.progressSubs[taskID] = append(s.progressSubs[taskID], ch)

	// 发送当前进度
	if task.Status == StatusCompleted || task.Status == StatusFailed || task.Status == StatusCancelled {
		ch <- 100
	} else {
		ch <- task.Progress
	}

	return ch, nil
}

// SubscribeResult 订阅任务结果
func (s *Scheduler) SubscribeResult(taskID uint) (<-chan *TaskResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	task, exists := s.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("任务不存在: %d", taskID)
	}

	ch := make(chan *TaskResult, 1)
	s.resultSubs[taskID] = append(s.resultSubs[taskID], ch)

	// 如果任务已完成，立即发送结果
	if task.Status == StatusCompleted || task.Status == StatusFailed || task.Status == StatusCancelled {
		result := &TaskResult{
			Success: task.Status == StatusCompleted,
			Message: task.Error,
		}
		if task.Status == StatusCompleted {
			result.Message = "任务执行成功"
		}
		select {
		case ch <- result:
		default:
		}
	}

	return ch, nil
}

// Cleanup 清理已完成的旧任务
// olderThan: 清理早于此时长的任务，0表示清理所有已完成的任务
func (s *Scheduler) Cleanup(olderThan time.Duration) int {
	s.mu.Lock()
	defer s.mu.Unlock()

	removed := 0

	for id, task := range s.tasks {
		// 只清理已完成的任务
		if task.Status != StatusCompleted && task.Status != StatusFailed && task.Status != StatusCancelled {
			continue
		}

		// 如果 olderThan 为 0，清理所有已完成任务
		if olderThan == 0 {
			delete(s.tasks, id)
			delete(s.progressSubs, id)
			delete(s.resultSubs, id)
			removed++
			continue
		}

		// 否则只清理早于指定时间的任务
		cutoff := time.Now().Add(-olderThan)
		if task.CompletedAt != nil && task.CompletedAt.Before(cutoff) {
			delete(s.tasks, id)
			delete(s.progressSubs, id)
			delete(s.resultSubs, id)
			removed++
		}
	}

	return removed
}

// Shutdown 关闭调度器
func (s *Scheduler) Shutdown(timeout time.Duration) error {
	s.mu.Lock()
	s.running = false
	s.mu.Unlock()

	// 等待所有 worker 完成
	done := make(chan struct{})
	go func() {
		for i := 0; i < cap(s.workerPool); i++ {
			s.workerPool <- struct{}{}
		}
		close(done)
	}()

	select {
	case <-done:
		return nil
	case <-time.After(timeout):
		return fmt.Errorf("关闭超时")
	}
}

// Stats 获取统计信息
type Stats struct {
	Total     int            `json:"total"`
	Pending   int            `json:"pending"`
	Running   int            `json:"running"`
	Completed int            `json:"completed"`
	Failed    int            `json:"failed"`
	Cancelled int            `json:"cancelled"`
	Workers   int            `json:"workers"`
	QueueSize int            `json:"queue_size"`
}

// GetStats 获取统计信息
func (s *Scheduler) GetStats() *Stats {
	s.mu.RLock()
	defer s.mu.RUnlock()

	stats := &Stats{
		Workers:   cap(s.workerPool),
		QueueSize: len(s.workerPool),
	}

	for _, task := range s.tasks {
		stats.Total++
		switch task.Status {
		case StatusPending:
			stats.Pending++
		case StatusRunning:
			stats.Running++
		case StatusCompleted:
			stats.Completed++
		case StatusFailed:
			stats.Failed++
		case StatusCancelled:
			stats.Cancelled++
		}
	}

	return stats
}
