import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/components/AppShell.vue'),
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '首页', icon: 'HomeFilled' }
      },
      {
        path: 'wizard',
        name: 'Wizard',
        component: () => import('@/views/Wizard.vue'),
        meta: { title: '创建任务', icon: 'Plus' }
      },
      {
        path: 'task/:id',
        name: 'TaskDetail',
        component: () => import('@/views/TaskDetail.vue'),
        meta: { title: '任务详情' }
      },
      {
        path: 'connections',
        name: 'Connections',
        component: () => import('@/views/Connections.vue'),
        meta: { title: '连接管理', icon: 'Connection' }
      },
      {
        path: 'collection',
        name: 'Collection',
        component: () => import('@/views/Collection.vue'),
        meta: { title: '数据采集', icon: 'Download' }
      },
      {
        path: 'analysis',
        name: 'Analysis',
        redirect: '/analysis/zombie',
        meta: { title: '分析结果', icon: 'DataAnalysis' },
        children: [
          {
            path: 'zombie',
            name: 'ZombieAnalysis',
            component: () => import('@/views/analysis/Zombie.vue'),
            meta: { title: '僵尸 VM' }
          },
          {
            path: 'rightsize',
            name: 'RightSizeAnalysis',
            component: () => import('@/views/analysis/RightSize.vue'),
            meta: { title: 'Right Size' }
          },
          {
            path: 'tidal',
            name: 'TidalAnalysis',
            component: () => import('@/views/analysis/Tidal.vue'),
            meta: { title: '潮汐检测' }
          },
          {
            path: 'health',
            name: 'HealthAnalysis',
            component: () => import('@/views/analysis/Health.vue'),
            meta: { title: '平台健康' }
          }
        ]
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { title: '任务中心', icon: 'List' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '系统设置', icon: 'Setting' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = to.meta.title + ' - JustFit'
  }

  // 检查是否有正在运行的任务，如果有任务正在运行且用户试图离开
  const runningTask = localStorage.getItem('justfit_running_task')
  if (runningTask && to.path !== '/' && !to.path.startsWith('/task/')) {
    // 可以在这里添加提示逻辑
  }

  next()
})

export default router
