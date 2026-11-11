# 给 Codex 的执行清单（第 2 轮：v3 修正 + 成片）

只执行，不要修改任何代码或着色器。任何一步报错，就停下来，把完整报错原文写进 `work/prev/v3_error.txt` 并提交推送。
`git push` 如果因为网络失败（例如 Could not resolve host），等几秒重试，最多 4 次，不算报错。

工作目录：`D:\mv`（仓库根目录），渲染命令在 `D:\mv\work` 下运行。

## 步骤

1. 拉取分支
   ```
   git checkout claude/mv-v3
   git pull origin claude/mv-v3
   ```
2. 重新生成书法大字的位置
   ```
   cd work
   python render.py layout
   ```
3. 渲染本轮改过的镜头的接触表
   ```
   python render.py sheet prev/v3_r2.jpg A6 B6b C3 C4 C7 D4 E7b
   ```
4. 提交并推送接触表和布局文件
   ```
   cd ..
   git add work/prev/v3_r2.jpg work/layout.json
   git commit -m "v3 round 2 preview sheet (GPU)"
   git push origin claude/mv-v3
   cd work
   ```
5. 渲染 1080p 成片（约 1 小时，不提交）
   ```
   python render.py video ..\山脚_MV_v3.mp4 0 196.6 2 > render_v3.log
   ```
6. 告诉用户：成片路径 `D:\mv\山脚_MV_v3.mp4`、`render_v3.log` 最后一行的耗时、`git push` 的输出。

## 不要做
- 不要覆盖 `山脚_MV_v2.mp4` 等旧成片。
