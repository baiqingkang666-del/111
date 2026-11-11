# 给 Codex 的执行清单（第 1 轮：v3 预览）

只执行，不要修改任何代码或着色器。任何一步报错，就停下来，把完整报错原文写进 `work/prev/v3_error.txt` 并提交推送。

工作目录：`D:\mv`（仓库根目录），渲染命令在 `D:\mv\work` 下运行。音频 `D:\mv\*.m4a` 保持原位。

## 步骤

1. 拉取分支
   ```
   git fetch origin
   git checkout claude/mv-v3
   git pull origin claude/mv-v3
   ```
2. 重新生成书法大字的位置（镜头改了，旧位置不再适用，约几分钟）
   ```
   cd work
   python render.py layout
   ```
3. 渲染 5 张接触表（960×540，每个镜头 3 帧）
   ```
   python render.py sheet prev/v3_a.jpg P00 A1 A2 A3 A4 A5 A6 A7
   python render.py sheet prev/v3_b.jpg B1 B2a B2b B3 B4 B5 B6a B6b B7 B8 B9 B10
   python render.py sheet prev/v3_c.jpg C1 C2 C3 C4 C5 C6 C7
   python render.py sheet prev/v3_d.jpg D1 D2 D3 D4 D5a D5b D6 D7 D8a D8b D9 D11 D12
   python render.py sheet prev/v3_e.jpg E1 E1b E2 E3 E4 E5 E6 E7a E7b Z1
   ```
4. 渲染全片低清预览（960×540，给用户本机观看，不提交）
   ```
   python render.py video ..\山脚_MV_v3_preview.mp4 0 196.6 -1
   ```
5. 提交并推送预览图和布局文件
   ```
   cd ..
   git add work/prev/v3_a.jpg work/prev/v3_b.jpg work/prev/v3_c.jpg work/prev/v3_d.jpg work/prev/v3_e.jpg work/layout.json
   git commit -m "v3 preview sheets (GPU)"
   git push origin claude/mv-v3
   ```
6. 把 `git push` 的输出，以及每条渲染命令的耗时告诉用户。

## 不要做
- 不要渲染 1080p 成片（等预览确认后再做）。
- 不要覆盖 `山脚_MV_v2.mp4` 等旧成片。
