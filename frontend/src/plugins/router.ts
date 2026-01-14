import {createRouter, createWebHistory} from 'vue-router'

export default createRouter({
  history: createWebHistory(import.meta.env.VITE_BASE_ROUTE || '/'),
  scrollBehavior: () => ({top: 0}),
  routes: [
    {
      path: '/',
      redirect: {name: 'start'}
    },
    {
      path: '/start',
      name: 'start',
      component: () => import('@/views/StartView.vue')
    },
    {
      path: '/chatbots',
      name: 'chatbots',
      meta: {hideFooter: true},
      component: () => import('@/views/ChatbotsView.vue'),
      children: [{
        path: ':endpoint/:chatId?',
        name: 'chat',
        component: () => import('@/views/ChatView.vue')
      }]
    },
    {
      path: '/help',
      name: 'help',
      component: () => import('@/views/HelpView.vue')
    },
    {
      path: '/imprint',
      name: 'imprint',
      component: () => import('@/views/ImprintView.vue')
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: {name: 'chatbots'}
    }
  ]
})
