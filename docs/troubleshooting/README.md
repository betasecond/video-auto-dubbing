# 故障排除文档

本目录包含常见问题的详细解决方案和故障排除指南。

## 📋 问题分类

### 🎵 音频处理问题
- [TTS FFmpeg Concat Error 254](./tts-ffmpeg-concat-error-254.md) - TTS音频合并失败解决方案

### 🌐 前端问题
- [前端任务刷新无限递归](./tts-ffmpeg-concat-error-254.md#方案二-前端无限递归修复) - 浏览器资源耗尽问题

### 🐳 容器部署问题
- [Docker缓存问题](./tts-ffmpeg-concat-error-254.md#关键经验教训) - 代码修改不生效的解决方案

## 🆘 快速问题定位

### 常见错误码
| 错误码 | 组件 | 描述 | 解决文档 |
|--------|------|------|----------|
| exit status 254 | TTS/FFmpeg | 音频合并失败 | [详细解决方案](./tts-ffmpeg-concat-error-254.md) |
| ERR_INSUFFICIENT_RESOURCES | 前端 | 浏览器连接耗尽 | [前端修复](./tts-ffmpeg-concat-error-254.md#方案二-前端无限递归修复) |

### 问题诊断流程
1. **收集错误信息** - 任务ID、错误消息、时间戳
2. **查看详细日志** - `docker-compose logs [service] --tail=100`
3. **检查服务状态** - `docker-compose ps`
4. **查阅解决文档** - 在本目录中找到对应问题
5. **应用解决方案** - 按文档步骤操作
6. **验证修复效果** - 重新测试原失败场景

## 🛠️ 调试工具

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs worker --tail=50

# 查找特定任务日志
docker-compose logs worker | grep "task_id_here"
```

### 数据库查询
```bash
# 连接数据库
docker-compose exec db psql -U dubbing -d dubbing

# 查看任务状态
SELECT id, status, error FROM tasks ORDER BY created_at DESC LIMIT 5;

# 查看segment信息
SELECT task_id, idx, tts_audio_key FROM segments WHERE task_id = 'your-task-id';
```

### 队列管理
```bash
# RabbitMQ管理界面
http://localhost:15673
# 用户名: rabbitmq, 密码: rabbitmq123

# 手动发送消息 (测试用)
curl -u rabbitmq:rabbitmq123 -H "Content-Type: application/json" \
  -X POST http://localhost:15673/api/exchanges/%2f/amq.default/publish \
  -d '{"properties":{"delivery_mode":2},"routing_key":"task.step","payload":"..."}'
```

## 📞 获取帮助

1. **查阅相关文档** - 检查是否有对应问题的解决方案
2. **收集完整信息** - 任务ID、错误日志、系统环境
3. **尝试常见解决方案** - 重启服务、清理缓存等
4. **创建问题记录** - 按模板记录问题详情和解决过程

## 📝 贡献指南

如果你解决了新的问题，请：

1. 在此目录创建详细的解决方案文档
2. 更新此README添加问题索引
3. 提交PR并描述解决的问题
4. 遵循现有文档的格式和结构

### 文档模板
```markdown
# 问题标题

## 问题概述
- 问题描述
- 影响范围
- 严重程度

## 错误详情
- 错误信息
- 相关日志

## 问题分析
- 可能原因
- 诊断过程

## 解决方案
- 修复步骤
- 代码修改
- 配置调整

## 验证结果
- 测试方法
- 成功指标

## 经验教训
- 关键发现
- 预防措施
```

---

最后更新: 2026年1月23日