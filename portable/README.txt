便携版使用说明

1. 双击 start.bat 启动服务。
2. 浏览器打开 http://127.0.0.1:8000 。
3. 首次启动会在本目录自动创建 data/，经营数据保存在其中，原始报表归档放入 data/imports/。
4. 双击 backup.bat 备份本目录 data/ 到上级目录 ecompass-backup/data/。

便携包不需要安装 Python。请保持 ecompass.exe、start.bat、backup.bat 和 README.txt 位于同一目录。整目录复制即可迁移数据库和测试数据；不要只复制 exe。
