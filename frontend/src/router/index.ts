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
  if (to.meta?.title) {
    document.title = to.meta.title + ' - JustFit'
  }
  next()
})

export default router
