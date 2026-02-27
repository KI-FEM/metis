import {createRouter, createWebHistory} from 'vue-router'
import { useStudyStore } from '@/stores/study'

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
      path: '/topics',
      name: 'topics',
      meta: {hideFooter: true},
      component: () => import('@/views/MainView.vue'),
      beforeEnter: async (to, from, next) => {
        const store = useStudyStore()
        if (!store.hasUserId())
          next({name: 'start'})
        else next()
      },
      children: [{
        path: ':endpoint',
        name: 'modules',
        component: () => import('@/views/TopicView.vue')
      }, {
        // TODO: if topic has skills but no skill is selected redirect to {name: 'topic'}
        path: ':endpoint/chat/:chatId?',
        name: 'chat',
        component: () => import('@/views/ChatView.vue')
      }]
    },
    {
      path: '/help',
      component: () => import('@/views/MainView.vue'),
      children: [{
        path: '',
        name: 'help',
        component: () => import('@/views/HelpView.vue')
      }, {
        path: 'faq',
        name: 'faq',
        component: () => import('@/views/HelpView.vue')
      }]
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/ImprintView.vue') // TODO
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
      path: '/study',
      name: 'study',
      component: () => import('@/views/StudyView.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: {name: 'topics'}
    }
  ]
})
