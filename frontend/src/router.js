import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/LoginView.vue'),
    meta: { bare: true },
  },
  {
    path: '/',
    name: 'welcome',
    component: () => import('./views/WelcomeView.vue'),
  },
  {
    path: '/departments/:id',
    name: 'department',
    component: () => import('./views/DepartmentView.vue'),
    props: true,
  },
  {
    path: '/employees/:login',
    name: 'employee',
    component: () => import('./views/EmployeeView.vue'),
    props: true,
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('./views/SearchView.vue'),
  },
  {
    path: '/admins',
    name: 'admins',
    component: () => import('./views/AdminsView.vue'),
    meta: { superadmin: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'welcome' }
  }
  if (to.meta.superadmin && !auth.isSuperadmin) {
    return { name: 'welcome' }
  }
})

export default router