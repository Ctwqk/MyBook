# 前端特定说明

## 技术栈

- React 18
- React Router 6
- Zustand (状态管理)
- Ant Design 5 (UI 组件库)
- Axios (HTTP 客户端)
- TypeScript
- Vite (构建工具)

## 开发

```bash
# 安装依赖
pnpm install

# 开发服务器
pnpm dev

# 构建
pnpm build

# 预览构建结果
pnpm preview
```

## 目录结构

```
frontend/
├── src/
│   ├── api/          # API 调用封装
│   ├── components/   # 通用组件
│   ├── pages/        # 页面组件
│   ├── store/        # Zustand 状态管理
│   ├── App.tsx       # 根组件
│   ├── main.tsx      # 入口文件
│   └── index.css     # 全局样式
├── public/
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 页面说明

### 项目列表页 (`/projects`)
- 显示所有项目
- 创建新项目
- 引导项目

### 创作台 (`/projects/:id`)
- 三栏布局:
  - 左侧: 故事设定/角色
  - 中间: 章节列表/操作
  - 右侧: 正文预览/摘要

### 记忆库 (`/projects/:id/memory`)
- Story Bible 查看/编辑
- 伏笔管理
- 记忆搜索
- 上下文包构建

### 发布页 (`/projects/:id/publish`)
- 发布任务列表
- 章节发布
- 平台适配器管理

## 状态管理

使用 Zustand 管理全局状态:

```typescript
// projectStore.ts
interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  setProjects: (projects: Project[]) => void
  // ...
}
```

## API 调用

统一使用 `src/api/index.ts` 中的封装:

```typescript
import { projectApi, chapterApi, memoryApi, publishApi } from '@/api'

// 示例
const projects = await projectApi.list()
const chapter = await chapterApi.generate(projectId, chapterId, { outline })
```
