# 安全与代码审查报告 — SCSBOA Score Studio v1.2.0

> 此报告是修复前的历史快照。七项发现已在 v1.2.1 中进行针对性修复，验证与剩余限制见 [SECURITY_FIXES.md](<C:/cloud coding/SCSBOA/SECURITY_FIXES.md>)。

- 日期：2026-10-27。
- 项目类型：Windows 本地 Python / PySide6 桌面程序，SQLite 存储，离线 OCR，图片/PDF 和 ZIP/JSON 资料包输入。
- 范围：scorestudio/、main.py、依赖锁定文件、打包配置、工具和测试；源代码与 v1.2.0 分享包内 source/ 一致。
- 结论：严重 0 · 高 1 · 中 5 · 低 1。包含安全风险与数据完整性缺陷，不代表发现了 7 个可远程利用的漏洞。
- 本次仅审查，未修改应用代码、依赖或用户资料库。安全复现使用 tmp/ 内临时资料库；未执行内存破坏、代码执行或耗尽资源的攻击。

## 高

### H-1：存在已知漏洞的 Pillow 解码器可被伪装扩展名触达

- 位置：[requirements-lock.txt:14](<C:/cloud coding/SCSBOA/requirements-lock.txt:14>)；[recognition.py:23](<C:/cloud coding/SCSBOA/scorestudio/recognition.py:23>)；[storage.py:67](<C:/cloud coding/SCSBOA/scorestudio/storage.py:67>)。
- 类别：存在已知漏洞的依赖、文件类型校验不足；CWE-787 / CWE-190。
- 证据：实际安装及锁定版本为 Pillow 12.1.0。Image.open(path) 未设置 formats，文件内容决定解码器；扩展名白名单不能限制实际图片格式。用无害的 1×1 RGB PSD 改名为 .png 后，stage_source 和 load_image 均接受并成功解码。
- 风险：用户导入或预览不可信文件即可到达 PSD 解码路径；官方确认受影响版本存在越界写，特制 PSD 可能导致崩溃或代码执行。这里验证的是路径可达性，不是已完成任意代码执行。PNG EXIF 解析也有已公布的耗时问题，当前 exif_transpose 会接触 EXIF。
- 建议：优先升级到覆盖当前公告的兼容修复版本（本次查到部分修复在 Pillow 13.0.0）；显式限定解码格式为应用真正支持的类型，拒绝内容与后缀不符的输入；随后回归 PNG/JPEG/TIFF/HEIF 及 PDF 渲染路径。仅升级到 12.1.1 不足以覆盖后续 PSD 修复。
- 依据：[CVE-2026-25990 官方公告](https://github.com/python-pillow/Pillow/security/advisories/GHSA-cfh3-3jmp-rvhc)、[CVE-2026-42311 官方公告](https://github.com/python-pillow/Pillow/security/advisories/GHSA-pwv6-vv43-88gr)、[CVE-2026-96643 官方公告](https://github.com/python-pillow/Pillow/security/advisories/GHSA-g4qv-2jxx-769h)。

## 中

### M-1：像素限制晚于解码，PDF 路径没有像素上限

- 位置：[recognition.py:17](<C:/cloud coding/SCSBOA/scorestudio/recognition.py:17>)、[recognition.py:24](<C:/cloud coding/SCSBOA/scorestudio/recognition.py:24>)；[app.py:151](<C:/cloud coding/SCSBOA/scorestudio/app.py:151>)。
- 类别：资源消耗/可用性；CWE-400。
- 证据：普通图片在 exif_transpose/convert 后才检查 40MP；PDF 分支渲染后直接返回，完全绕过该检查。安全拦截 render 的测试显示：2500×2000 point 页面、scale=3 会进入预计 45,000,000 像素的渲染调用。测试在分配位图前主动停止。
- 风险：文件字节数很小也可能解码出巨量像素；加载、预览及 OCR 可消耗大量内存。预览在 UI 线程执行，原生解码也无法靠普通线程取消及时中断。
- 建议：在解码前检查图像尺寸；PDF 依据页面尺寸和 scale 预估像素与内存，超限缩放或拒绝；每页和整批均设上限。后续可将不可信文件解码隔离到有超时和内存预算的子进程。

### M-2：数值验证接受字符串，但没有归一化，合法性检查和显示要求不一致

- 位置：[model.py:89](<C:/cloud coding/SCSBOA/scorestudio/model.py:89>)；[ui_common.py:32](<C:/cloud coding/SCSBOA/scorestudio/ui_common.py:32>)。
- 类别：输入校验；CWE-20。
- 证据：scores.total="78.2" 可通过 validate，因为 number() 返回的浮点值未写回记录；fmt() 随后对字符串执行数值格式化而抛出 ValueError。布尔值也可被 float() 当作数字接受。
- 风险：异常或第三方生成的资料包通过读取校验，却在待核对页面加载时失败；直接复用存储接口还可持久化不一致数据。当前 UI 通常在保存前就报错，不能据此声称所有此类包都会污染正式资料库。
- 建议：为资料包建立严格 JSON schema，分数只接受有限 int/float/null 且明确排除 bool；或在边界统一转换后返回规范记录。拒绝非法类型时给出记录与字段位置。

### M-3：切换评分体系的冲突处理仍会混合不同体系的分数

- 位置：[model.py:60](<C:/cloud coding/SCSBOA/scorestudio/model.py:60>)、[model.py:128](<C:/cloud coding/SCSBOA/scorestudio/model.py:128>)；[storage.py:99](<C:/cloud coding/SCSBOA/scorestudio/storage.py:99>)。
- 类别：数据完整性/业务逻辑。
- 证据：identity 不包含 scheme；merge_records 先合并评分字段，再将 scheme 作为单独冲突项。复现中旧体系 music.total=31.8、新体系 ge.total=99，选择 incoming scheme 后保存为同一记录，保留两套分数。选择旧 scheme 也不能阻止无冲突的新分项补入。
- 风险：界面虽然按体系筛选，底层记录已混合不同量表，导致趋势与对比错误。
- 建议：scheme 不同的记录禁止逐字段合并；选择整条替换或作为独立记录保存。若将 scheme 纳入唯一键，需要明确旧库迁移和重复记录处理规则。

### M-4：合并结果没有重新验证，可保存随后无法导入的奖项记录

- 位置：[model.py:131](<C:/cloud coding/SCSBOA/scorestudio/model.py:131>)；[storage.py:108](<C:/cloud coding/SCSBOA/scorestudio/storage.py:108>)。
- 类别：数据完整性/输入校验。
- 证据：两条输入分别含 Best Music 和 best music，各自均合法；按字典键合并后不会产生冲突，记录成功保存，但对合并结果执行 validate 会报 Duplicate award name。两批各不超过 100 项的奖项也可能合并后超过上限。
- 风险：数据库包含不符合自身格式约束的数据，导出的资料包可能被同一 App 拒绝，奖项编辑也可能受阻。
- 建议：按规范化奖名检测冲突；对每个最终合并记录及整个待提交结果重新验证，失败时回滚整批，保留可读错误说明。

### M-5：原图缓存非原子写入且不复核已有文件，损坏后有效资料包无法修复

- 位置：[storage.py:71](<C:/cloud coding/SCSBOA/scorestudio/storage.py:71>)、[storage.py:174](<C:/cloud coding/SCSBOA/scorestudio/storage.py:174>)。
- 类别：附件完整性/异常恢复。
- 证据：文件复制和 write_bytes 直接写最终名称；已有文件只判断 exists。测试将临时资料库中的原图替换为损坏内容，再导入含正确原图、哈希验证通过的资料包，旧损坏文件仍被保留。
- 风险：进程中断、磁盘错误或本地修改造成缓存损坏后，重新导入不能恢复原图；再次导出的附件与哈希不符，其他用户会导入失败。本项需要已有缓存损坏，不是“任意资料包能绕过路径保护”。
- 建议：临时文件写入、校验后用原子替换；已有缓存应复核哈希，异常时从有效包恢复；导出前检查附件完整性并定位损坏原图。

## 低（当前部署条件下的条件性风险）

### L-1：pdfminer.six 仍含已公布的 CMap pickle 加载问题

- 位置：[requirements-lock.txt:11](<C:/cloud coding/SCSBOA/requirements-lock.txt:11>)、[recognition.py:213](<C:/cloud coding/SCSBOA/scorestudio/recognition.py:213>)；本机依赖 [.venv/Lib/site-packages/pdfminer/cmapdb.py:252](<C:/cloud coding/SCSBOA/.venv/Lib/site-packages/pdfminer/cmapdb.py:252>)。
- 类别：不安全反序列化依赖；CVE-2025-70559 / CWE-502。
- 证据：安装版本 20251107 仍调用 pickle.loads，并读取 CMAP_PATH。官方修复版本为 >=20251230。
- 条件与定级：公告上游为 High，但利用需要攻击者能向 CMap 搜索目录写入文件，并由不同权限的进程加载。当前程序没有把资料包附件目录设置成 CMAP_PATH，也没有发现提权请求；因此没有证据证明普通成绩 PDF 单独能在本应用触发这条利用链，当前部署按低优先级条件性风险记录。
- 建议：连同 pdfplumber 一起升级并回归 PDF OCR。pdfplumber 0.11.8 精确要求 pdfminer.six==20251107，不能只强行替换后者；避免管理员运行及可被他人写入的 CMap 路径。
- 依据：[维护者安全公告](https://github.com/pdfminer/pdfminer.six/security/advisories/GHSA-f83h-ghpp-7wcc)。

## 依赖核查与未直接计为可利用漏洞的项目

本次逐一查询 PyPI 官方版本接口，30 项锁定依赖全部返回。Pillow、pdfminer.six、pillow_heif 有公告记录。公告存在重复 CVE/GHSA/PYSEC 条目，不能把原始条目数当作独立漏洞数。结果保存在 [依赖摘要](<C:/cloud coding/SCSBOA/tmp/security-dependency-summary.json>)；没有运行 pip-audit，也未自动升级依赖。

- pillow_heif 1.2.0：CVE-2026-28231 在编码缓冲区校验，公告列修复 1.3.0。本应用读取 HEIF，未发现生产路径编码攻击者提供的 HEIF 图像；不计作已确认可触达高危项。建议下一轮依赖升级一并处理。依据：[维护者公告](https://github.com/bigcat88/pillow_heif/security/advisories/GHSA-5gjj-6r7v-ph3x)。
- Qt 6.10.1：CVE-2025-14576 涉及 Qt Quick VectorImage 载入 SVG。本应用使用 Qt Widgets，未使用该组件，不据此宣布存在 QML 注入。依据：[Qt 官方公告](https://www.qt.io/blog/security-advisory-qml-code-injection-in-vectorimage)。
- Pillow 部分字体、编码器、后续帧、Arrow 接口公告没有对应调用证据；未逐条计为应用漏洞。但 PSD 解码路径和 PNG EXIF 路径已具备调用依据，应优先处理 H-1。
- PyPI 没有列出漏洞不代表没有漏洞；原生 DLL 及其内嵌库并未完成全量二进制漏洞映射。

## 已确认的防护与正常行为

- 应用代码未发现硬编码凭证、主动 HTTP 上传、遥测、shell 命令拼接、eval 或业务层 pickle 反序列化。
- SQLite 涉及用户值的查询使用参数绑定；保存批次使用事务，冲突取消不提交。
- 资料包不执行 extractall；仅允许哈希命名、类型白名单内的附件，校验包内附件哈希；限制解压总量、清单大小、条目数及重复 ZIP 名。
- 主要标签强制 PlainText；成绩/学校文本没有被插入 WebView 或 JavaScript。
- 待核对成绩不自动成为正式记录；正常退出会询问丢弃未保存批次；主入口有资料库锁。
- 本地 SQLite 和导出 ZIP 未加密，但没有凭证字段。保留原图、EXIF 等元数据以及撤销附件是现有产品行为，不是秘密上传；分享者仍需核对原图是否含个人信息。

## 实际执行的验证及限制

- 17 项单元测试通过；Qt 点击详情、分组排名、默认学校、导入核对、资料包与撤销集成检查通过。
- pip check 通过；它仅检查依赖兼容，不等于漏洞检查。
- 5 个无害异常场景复现见 [结果 JSON](<C:/cloud coding/SCSBOA/tmp/security-reproduction-results.json>)；另使用拦截渲染验证 45MP PDF 进入分配前调用，无实际大内存分配。
- 没有读取或修改正在运行的个人资料库，没有执行漏洞利用载荷，没有安装扫描器或改动依赖。
- 未做完整恶意文件模糊测试、运行时网络抓包、Windows ACL 渗透、所有 DLL/解码器的二进制审计；结论仅针对当前检查范围。

## 建议整改顺序与验收

1. H-1 与 M-1：先修依赖及输入解码边界。验收：伪装 PSD 被拒绝，超大尺寸在分配前被拒绝/缩放，正常参考图与 PDF 识别不退化。
2. M-2/M-4：严格输入类型及最终结果验证。验收：字符串/布尔分数、合并后的重复奖名和超限奖项均不能进入正式库。
3. M-3：明确跨体系记录策略。验收：不同体系的同校同场成绩不能被静默补成一个混合记录。
4. M-5：原图原子写入与缓存修复。验收：模拟中断/损坏后有效包可恢复原图，导出附件通过哈希校验。
5. L-1：兼容升级 PDF 依赖，重新打包并对离线 OCR、资料包兼容和 Windows EXE 做回归。

## 不适用项

Android/iOS 权限、浏览器 Cookie/CSP/CORS、服务端鉴权/JWT、网络 TLS pinning、登出令牌清理：当前是无账号、无服务端的 Windows 本地应用，未实现对应功能。
