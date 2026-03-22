import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  base: '/WordAgent/',
  title: "WordAgent",
  description: "文策AI——基于WPS/Microsoft Word加载项的AI辅助写作系统",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: '/WenceAI_small.png',

    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/guide/quick-start' },
      { text: '下载', link: 'https://github.com/visresearch/WordAgent/releases' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: '指南',
          items: [
            { text: '项目介绍', link: '/guide/introduction' },
            { text: '快速开始', link: '/guide/quick-start' },
            { text: '使用说明', link: '/guide/usage' },
            { text: '系统架构', link: '/guide/architecture' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/visresearch/WordAgent' }
    ],

    footer: {
      message: '基于 Apache License 2.0 开源协议',
      copyright: 'Copyright © 2026 WordAgent'
    },

    outline: {
      label: '页面导航'
    }
  }
})
