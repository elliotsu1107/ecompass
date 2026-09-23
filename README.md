# 电商经营罗盘（ecompass）

电商经营数据看板，面向淘宝/天猫双店铺团队。系统运行在办公室 Windows 电脑上，使用 SQLite 保存经营数据，通过局域网浏览器查看店铺、类目和运营 OKR 指标。

> 当前版本为 v0.1.2 内测版，适合办公室内网真实报表验证。

## 功能

- 店铺、类目、运营和产品基础资料管理
- 店铺销售日报导入
- 商品销售日报导入
- 商品级推广报表导入
- Excel / XLS 多行表头识别
- CSV 自动尝试 UTF-8、GB18030 和 GBK 编码
- 每个店铺、每种报表独立配置列映射
- 商品 ID 匹配产品清单中的类目和运营负责人
- 商品、推广数据按日期和业务键增量更新
- 同商品多条推广记录自动聚合
- 商品和推广事实保存导入时的类目、运营归属快照
- 店铺、类目、运营结算销售额和推广费比
- 两店合计运营 OKR 及店铺金额占比
- 店铺日报与商品日报结算额对账告警
- 原始文件 SHA-256 归档和导入日志

## 指标口径

```text
结算销售额 = 支付金额 - 退款金额
推广费比 = 推广花费 / 结算销售额
目标完成进度 = 当月累计结算销售额 / 月目标
```

当计算分母为 0 或目标未设置时，页面显示 `—`。

目标粒度如下：

- 店铺目标：月份 + 店铺
- 类目目标：月份 + 店铺 + 类目
- 运营 OKR：月份 + 运营负责人，两店铺类目合计

## 技术栈

- Python 3.14
- FastAPI
- Uvicorn
- SQLite
- Pandas
- OpenPyXL / xlrd
- Jinja2
- 原生 JavaScript
- Pytest

## 环境要求

- Windows 10 或 Windows 11
- Python 3.14
- Git
- PowerShell

确认环境：

```powershell
py --version
git --version
```

## 安装

```powershell
git clone https://github.com/elliotsu1107/ecompass.git
cd ecompass
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 启动

PowerShell：

```powershell
.venv\Scripts\python.exe run.py
```

Windows 批处理脚本：

```powershell
.\start.bat
```

浏览器打开：

```text
http://127.0.0.1:8000
```

管理员页面：

```text
http://127.0.0.1:8000/login
```

当前 v0.1.2 内测版默认管理员账号：

```text
账号：admin
密码：ecompass123
```

正式部署前请修改认证配置。当前默认账号密码仅用于 v0.1.2 内测，不建议直接用于长期生产环境。

## 局域网访问

启动电脑监听 `0.0.0.0:8000`。在办公室电脑上查看内网 IP：

```powershell
ipconfig
```

其他同事使用同一局域网访问：

```text
http://<办公室电脑内网IP>:8000
```

如其他电脑无法访问，请在管理员 PowerShell 中放行端口：

```powershell
netsh advfirewall firewall add rule name="ecompass" dir=in action=allow protocol=TCP localport=8000
```

## 基础资料与报表导入

管理后台地址：

```text
http://127.0.0.1:8000/admin
```

未登录访问 `/admin` 或 `/import` 会自动跳转到登录页。看板右上角也有「后台管理」入口。

按后台页面从上到下依次配置：

1. 运营人员（姓名）。
2. 店铺（店铺名称 + 平台）。
3. 类目（类目名称 + 负责运营，必须绑定运营）。
4. 商品：可以批量导入，也可以逐个新增。
5. 月度目标（先选月份，再填店铺目标、类目目标、运营目标）。

商品清单支持 Excel / CSV 批量导入，列名支持以下写法：

```text
店铺名称（或 店铺）
商品ID（或 商品id / 宝贝ID）
商品名称（或 商品名 / 宝贝名称）
类目（或 类目名称 / 分类）
运营负责人（或 运营 / 负责人）
```

导入说明：

- 店铺必须已经在第 2 步建立，未匹配的店铺会在结果里列出店名。
- 类目和运营不存在时会自动创建。
- 同一个商品重复导入会更新，不会产生重复记录。
- Excel 里被识别成数字的商品 ID 会自动去掉小数点。

资料配置完成后，到 `http://127.0.0.1:8000/import` 导入报表：

1. 两个店铺的店铺报表。
2. 两个店铺的商品报表。
3. 两个店铺的商品级推广报表。

导入页底部会显示最近的导入记录。商品和推广报表按商品 ID 匹配商品清单中的类目与运营；未匹配商品会在导入结果中提示。

常见字段对应关系：

| 系统字段 | 店铺报表 | 商品报表 | 推广报表 |
| --- | --- | --- | --- |
| 日期 | 统计日期 | 统计日期 | 日期 |
| 商品 ID | 不需要 | 商品ID | 主体ID |
| 商品名称 | 不需要 | 商品名称 | 主体名称 |
| 支付金额 | 支付金额 | 支付金额 | 不需要 |
| 退款金额 | 成功退款金额 | 成功退款金额 | 不需要 |
| 店铺推广花费 | 全站推广花费 | 不需要 | 不需要 |
| 推广花费 | 不需要 | 不需要 | 花费 |
| 推广成交金额 | 不需要 | 不需要 | 总成交金额 |

不同店铺的表头可以不同。系统按“店铺 + 文件类型 + 表头签名”保存独立映射。Excel / XLS 表头不要求位于第一行，系统会扫描前 20 行并推荐候选表头。

## 数据存储

运行数据默认保存于项目下的 `data/`：

```text
data/ecompass.db
data/secret.key
data/imports/
```

这些目录包含经营数据和原始报表，已加入 `.gitignore`，不会提交到 GitHub。

备份数据：

```powershell
.\backup.bat
```

默认备份到项目上级目录：

```text
D:\Dev\ecompass-backup\data
```

## 测试

安装依赖后运行：

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

## 自动化测试覆盖

- 应用健康检查和数据库 Schema
- 认证逻辑
- 基础资料和目标业务键
- Excel / CSV 解析
- 增量导入和重复推广行聚合
- 结算销售额、推广费比和对账告警
- 原有 SQLite 数据库启动时会自动补齐商品日报字段，不清空历史数据。
- 后台支持模块切换、基础资料编辑删除、商品按店铺切换和引用保护。
- 已用两店真实店铺、商品、推广报表完成接口级导入回归。

## 便携版构建

在 Windows PowerShell 中执行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_portable.ps1
```

构建结果为 `dist/ecompass-portable/` 和 `dist/ecompass-portable.zip`。便携包包含 `ecompass.exe`、`start.bat`、`backup.bat` 和 `README.txt`；模板与静态资源已嵌入程序目录，运行数据不会打入包。首次启动便携版时，程序会在便携包根目录创建 `data/`，数据库、密钥和导入文件均保存在其中。

## 便携版升级

升级时不需要重新录入数据，按以下步骤操作：

1. 退出旧版本 `ecompass.exe`。
2. 先复制整个旧目录作为备份，或至少备份 `data/`，包括 `data/ecompass.db`、`data/secret.key` 和 `data/imports/`。
3. 解压新的 `ecompass-portable.zip`。
4. 将新包中的程序文件复制到旧便携版目录并覆盖同名文件。
5. 保留旧目录中的 `data/`，不要用新包中的空 `data/` 覆盖；也不要覆盖旧的 `data/secret.key`。
6. 双击新的 `start.bat` 启动并检查看板与历史数据。

推荐先执行：

```powershell
Copy-Item D:\Tools\ecompass D:\Tools\ecompass-backup-0.1.0 -Recurse
```

便携版升级本质上是“覆盖程序文件、保留 data 数据目录”。不要只复制 `ecompass.exe`，也不要删除旧目录的 `data/`。


确认手动启动和局域网访问正常后，可以使用管理员 PowerShell 创建登录时启动任务：

```powershell
schtasks /Create /TN "ecompass" /SC ONLOGON /TR "D:\Dev\ecompass\start.bat" /F
```

## 当前限制

- 当前主要支持本地 SQLite，不支持多机同时写入。
- 需要先维护产品清单，商品和推广报表才能正确归属类目与运营。
- 当前默认管理员密码用于内测，正式部署前应增加安全配置。
- 当前不包含平台 API 自动同步、公网访问、多级权限和消息推送。

## 隐私说明

本项目设计为办公室内网运行，经营数据默认留在本地电脑。请勿将真实报表、SQLite 数据库、密钥或其他经营资料提交到公共仓库。项目已通过 `.gitignore` 排除 `docs/`、`docs/exp/` 和 `data/`。

## 许可证

项目暂未指定开源许可证，当前仅用于内部试运行和开发验证。
