import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  base: '/WordAgent/',
  title: "WordAgent | 文策AI",
  description: "文策AI——基于WPS/Microsoft Word加载项的AI辅助写作系统",
  head: [
    ['link', { rel: 'icon', href: '/WordAgent/robot.ico' }],
  ],
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: '/WenceAI.png',

    nav: [
      { text: '首页', link: '/' },
      { text: '快速开始', link: '/guide/introduction' },
      { text: '下载', link: 'https://github.com/visresearch/WordAgent/releases' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: '快速开始',
          items: [
            { text: '项目简介', link: '/guide/introduction' },
            { text: '项目架构', link: '/guide/architecture' },
            { text: '安装方式', link: '/guide/installation' },
          ]
        },
        {
          text: '使用说明',
          items: [
            { text: '安装 WPS Word 加载项', link: '/guide/wps-plugin' },
            { text: '启动 Microsoft Word 加载项', link: '/guide/msword-plugin' },
            { text: '配置 API Key', link: '/guide/api-config' },
            { text: '个性化配置', link: '/guide/personalization' },
            { text: 'MCP 服务器配置', link: '/guide/mcp' },
            { text: 'Skill 配置', link: '/guide/skills' },
            { text: '数据管理', link: '/guide/data-management' },
            { text: '如何提问', link: '/guide/how-to-ask' },
            { text: '功能按钮说明', link: '/guide/features' },
            { text: '常见问题', link: '/guide/faq' },
          ]
        },
        {
          text: '关于',
          items: [
            { text: '关于作者', link: '/guide/about' },
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
