# 字幕模式默认值修改说明

## 📝 修改内容

将默认字幕模式从 **外挂字幕 (EXTERNAL)** 改为 **硬烧录 (BURN)**

## 🎯 修改原因

1. ✅ 硬烧录功能已验证正常
2. ✅ 用户体验更好（无需单独加载字幕文件）
3. ✅ 适合大多数使用场景

## 📦 修改文件清单

### 前端 (3个文件)

1. **frontend/app/tasks/new/page.tsx**

   ```typescript
   // 修改前
   const [subtitleMode, setSubtitleMode] = useState<SubtitleMode>('external');

   // 修改后
   const [subtitleMode, setSubtitleMode] = useState<SubtitleMode>('burn');
   ```

   ```tsx
   // 选项顺序调整，烧录字幕置顶并标记为推荐
   <SelectItem value="burn">
     <span>烧录字幕（推荐）</span>
   </SelectItem>
   <SelectItem value="external">
     <span>外挂字幕</span>
   </SelectItem>
   ```

2. **frontend/components/upload-form.tsx**

   ```typescript
   // 修改前
   subtitle_mode: 'external',

   // 修改后
   subtitle_mode: 'burn',
   ```

   ```html
   <!-- 选项顺序和文案调整 -->
   <option value="burn">烧录字幕（推荐 - 嵌入视频画面）</option>
   <option value="external">外挂字幕（生成 .ass 文件，可单独下载）</option>
   ```

### 后端 (5个文件)

1. **backend/app/api/tasks.py**

   ```python
   # 修改前
   subtitle_mode: str = Form("external", description="...")

   # 修改后
   subtitle_mode: str = Form("burn", description="...")
   ```

   API 文档说明更新：
   - burn: 将字幕烧录到视频中（**推荐，默认**）
   - external: 生成外挂字幕文件
   - none: 不生成字幕

2. **backend/app/models/task.py**

   ```python
   # 修改前
   subtitle_mode: Mapped[SubtitleMode] = mapped_column(
       Enum(SubtitleMode), nullable=False, default=SubtitleMode.EXTERNAL
   )

   # 修改后
   subtitle_mode: Mapped[SubtitleMode] = mapped_column(
       Enum(SubtitleMode), nullable=False, default=SubtitleMode.BURN
   )
   ```

3. **backend/app/schemas/task.py** (2处)

   ```python
   # TaskCreate
   subtitle_mode: SubtitleMode = Field(
       default=SubtitleMode.BURN,  # 改为 BURN
       description="字幕模式: burn=烧录到视频(推荐,默认), ..."
   )

   # TaskResponse
   subtitle_mode: SubtitleMode = Field(
       default=SubtitleMode.BURN,  # 改为 BURN
       description="字幕模式"
   )
   ```

4. **backend/app/services/task_service.py**

   ```python
   # 修改前
   subtitle_mode=getattr(task_data, 'subtitle_mode', SubtitleMode.EXTERNAL),

   # 修改后
   subtitle_mode=getattr(task_data, 'subtitle_mode', SubtitleMode.BURN),
   ```

5. **backend/app/workers/tasks.py**

   ```python
   # 修改前
   subtitle_mode = task.subtitle_mode or SubtitleMode.EXTERNAL

   # 修改后
   subtitle_mode = task.subtitle_mode or SubtitleMode.BURN
   ```

### 数据库迁移 (1个文件)

1. **backend/migrations/versions/005_change_subtitle_mode_default.py**
   - 新增迁移脚本
   - 将数据库表默认值从 'EXTERNAL' 改为 'BURN'

## 🔄 迁移步骤

### 本地开发环境

```bash
# 1. 重启后端服务（代码已修改）
pkill -f "uvicorn app.main"
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# 2. 运行数据库迁移（更新默认值）
cd backend && uv run alembic upgrade head

# 3. 前端无需重启（热重载自动生效）
```

### Docker 部署环境

```bash
# 1. 停止服务
docker-compose -f docker-compose.v2.yml down

# 2. 重新构建（代码已修改）
docker-compose -f docker-compose.v2.yml build

# 3. 启动服务
docker-compose -f docker-compose.v2.yml up -d

# 4. 运行数据库迁移
docker-compose -f docker-compose.v2.yml exec api alembic upgrade head
```

## ✅ 验证方法

### 1. 前端验证

访问 <http://localhost:3000/tasks/new>

- [ ] 字幕模式下拉框默认选中 "烧录字幕（推荐）"
- [ ] 选项顺序：烧录 > 外挂 > 不生成

### 2. API 验证

```bash
# 查看 API 文档
curl http://localhost:8000/api/v1/docs

# 检查默认值
curl -X POST http://localhost:8000/api/v1/tasks \
  -F "video=@test.mp4" \
  -F "source_language=en" \
  -F "target_language=zh"
# subtitle_mode 应自动为 "burn"
```

### 3. 数据库验证

```bash
# 检查表默认值
docker-compose exec db psql -U dubbing -d dubbing -c "\d+ tasks"
# subtitle_mode 列的 default 应为 'BURN'::subtitlemode
```

## 📊 影响分析

### 已有任务

- ✅ **不受影响** - 已创建的任务保持原有字幕模式
- ✅ 数据库迁移仅修改默认值，不修改现有数据

### 新建任务

- ✅ 默认使用烧录字幕
- ✅ 用户仍可手动选择其他模式

### API 调用

- ✅ 兼容性：未指定 subtitle_mode 参数时，默认为 burn
- ✅ 向后兼容：可以显式指定 external 或 none

## 🎨 UI 变化对比

### 修改前

```
字幕模式: [外挂字幕（推荐）▼]
  - 外挂字幕（推荐）
  - 烧录字幕
  - 不生成字幕
```

### 修改后

```
字幕模式: [烧录字幕（推荐）▼]
  - 烧录字幕（推荐）
  - 外挂字幕
  - 不生成字幕
```

## 📝 API 文档变化

### 修改前

```
subtitle_mode (可选，默认 external)
  - external: 生成外挂字幕文件（默认）
  - burn: 将字幕烧录到视频中
  - none: 不生成字幕
```

### 修改后

```
subtitle_mode (可选，默认 burn)
  - burn: 将字幕烧录到视频中（推荐，默认）
  - external: 生成外挂字幕文件
  - none: 不生成字幕
```

## ⚠️ 注意事项

1. **处理时间**
   - 烧录字幕比外挂字幕稍慢（需要视频重新编码）
   - 适用于大多数场景

2. **文件大小**
   - 烧录字幕文件略大（字幕渲染到画面）
   - 可接受的差异

3. **灵活性**
   - 烧录后无法关闭字幕
   - 外挂字幕可在播放器中开关

4. **回滚**
   - 如需回滚，运行 `alembic downgrade -1`
   - 或手动修改代码和数据库

## ✨ 优势总结

### 烧录字幕的优点

- ✅ 无需单独加载字幕文件
- ✅ 兼容所有播放器
- ✅ 字幕不会丢失或不同步
- ✅ 适合分享和发布

### 外挂字幕的优点

- ✅ 可以开关字幕
- ✅ 可以替换字幕
- ✅ 处理速度稍快
- ✅ 文件体积稍小

## 🔄 版本信息

- **修改日期**: 2026-02-08
- **版本**: v2.0.0+
- **影响范围**: 默认配置，不破坏现有功能
- **兼容性**: 完全向后兼容

---

**总结**: 本次修改将硬烧录设为默认选项，同时保留其他选项的可选性，提升了用户体验。
