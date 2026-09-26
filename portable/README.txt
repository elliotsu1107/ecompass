电商经营罗盘 v0.1.3 内测版 - Windows 便携包使用说明

1. 双击 start.bat 启动服务，等待约 2 秒后会自动打开默认浏览器访问 http://127.0.0.1:8000 。
2. 浏览器打开 http://127.0.0.1:8000 。
3. 首次启动会在本目录自动创建 data/，经营数据保存在其中，原始报表归档放入 data/imports/。
4. 双击 backup.bat 备份本目录 data/ 到上级目录 ecompass-backup/data/。

便携包不需要安装 Python。请保持 ecompass.exe、start.bat、backup.bat 和 README.txt 位于同一目录。整目录复制即可迁移数据库和测试数据；不要只复制 exe。

升级说明：
1. v0.1.3 启动时会自动为旧数据库补齐商品日报字段，保留原有历史记录。
2. 退出旧版本 ecompass.exe。
3. 先备份旧目录，至少保留 data/ecompass.db、data/secret.key 和 data/imports/。
4. 解压新的便携包，将程序文件覆盖到旧目录。
5. 保留旧目录的 data/，不要覆盖 data/secret.key，也不要只复制 exe。
6. 双击新的 start.bat 启动。
