# 电商经营罗盘（ecompass）

电商经营数据看板，面向淘宝/天猫双店铺团队。系统运行在办公室 Windows 电脑上，使用 SQLite 保存经营数据，通过局域网浏览器查看店铺、类目和运营 OKR 指标。

> 当前版本为 MVP，适合内部试运行和真实报表联调。

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

当前 MVP 默认管理员账号：

```text
账号：admin
密码：ecompass123
```

正式部署前请修改认证配置。当前版本默认账号密码仅用于内部 MVP 测试，不建议直接用于长期生产环境。

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

## 报表导入

推荐按以下顺序导入：

1. 配置两个店铺。
2. 配置运营和类目。
3. 导入产品清单。
4. 导入两个店铺的店铺销售日报。
5. 导入两个店铺的商品销售日报。
6. 导入两个店铺的商品级推广报表。
7. 设置店铺、店铺类目和运营 OKR 月目标。
8. 在看板核对指标和对账告警。

产品清单通过商品 ID 关联商品报表和推广报表，至少需要：

```text
店铺名称
商品ID
商品名称
类目
运营负责人
```

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

当前 MVP 测试覆盖：

- 应用健康检查和数据库 Schema
- 认证逻辑
- 基础资料和目标业务键
- Excel / CSV 解析
- 增量导入和重复推广行聚合
- 结算销售额、推广费比和对账告警
- 店铺、类目、运营看板接口

## 开机启动

确认手动启动和局域网访问正常后，可以使用管理员 PowerShell 创建登录时启动任务：

```powershell
schtasks /Create /TN "ecompass" /SC ONLOGON /TR "D:\Dev\ecompass\start.bat" /F
```

## 当前限制

- 当前主要支持本地 SQLite，不支持多机同时写入。
- 需要先维护产品清单，商品和推广报表才能正确归属类目与运营。
- 当前默认管理员密码用于 MVP 测试，正式部署前应增加安全配置。
- 当前不包含平台 API 自动同步、公网访问、多级权限和消息推送。

## 隐私说明

本项目设计为办公室内网运行，经营数据默认留在本地电脑。请勿将真实报表、SQLite 数据库、密钥或其他经营资料提交到公共仓库。项目已通过 `.gitignore` 排除 `docs/`、`docs/exp/` 和 `data/`。

## 许可证

项目暂未指定开源许可证，当前仅用于内部试运行和开发验证。
