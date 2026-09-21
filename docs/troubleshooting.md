# 故障排查

先检查本机 MinIO，再检查隧道，最后检查第三方配置。不要仅凭一个页面能打开就认定 S3 读写成功。

| 现象 | 优先检查 | 处理方向 |
| --- | --- | --- |
| `9000` 或 `9001` 被占用 | `Get-NetTCPConnection -State Listen -LocalPort 9000,9001` | 通过 PID 确认进程，避免重复启动；不要误杀其他服务 |
| DPAPI / Import-Clixml 解密失败 | 是否换了 Windows 用户或电脑 | 在实际运行账号下重新执行凭据脚本 |
| 本机 HTTPS 提示未知证书 | 本地 CA 是否导入正确用户/程序的信任库 | 导入公共 CA；CLI 可显式指定 `--cacert` |
| 证书 IP 不匹配 | 访问 IP 是否在 SAN 中；IP 是否变化 | 使用已有 SAN 地址，或重新签发包含新地址的服务端证书 |
| Schannel 提示吊销服务器不可达 | 私有 CA 没有在线 CRL | 本仓库 curl 检查使用 `--ssl-revoke-best-effort`，仍验证信任链和主机名 |
| 内网能访问网页，程序仍报证书错 | 程序可能使用 JVM/容器/自带 CA 库 | 在程序真正使用的信任库配置 CA |
| 内网另一台机器连接超时 | IP、网段、Wi-Fi 客户端隔离、VPN、防火墙 | 确认到 `9000` 的路径；按需放行 Private/LocalSubnet，不关闭防火墙 |
| 公共隧道域名打开是 502 | MinIO 未启动，源站 TLS 校验失败 | 先通过本机状态检查，再核对 CA 路径与 `localhost` SAN |
| 公共域名失效或连接不到隧道 | 进程退出、电脑睡眠、断网、旧域名 | 重新运行 `Start-Public-Tunnel.ps1`；脚本现在会先检查已保存地址的公共健康状态，失效时自动重建并输出新 Endpoint，然后更新第三方配置 |
| Tunnel 分配地址但一直连不上 | 出站网络或代理拦截，TCP 7844 不通 | 按网络策略允许 cloudflared 必要的出站访问，查看日志 |
| Quick Tunnel 启动异常且已有 Cloudflare 配置 | 用户 `.cloudflared` 目录已有 `config.yaml` | 核对官方 Quick Tunnel 配置冲突说明；先备份并辨别其他隧道用途，不盲目删除 |
| 浏览器打开 S3 根地址显示 XML / AccessDenied | 打开的是 API，且没有 S3 签名 | 可能是正常响应；健康检查用 `/minio/health/ready`，管理页面用本机 `9001` |
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` | 用户名密码、时钟、Region、签名、Host、地址路径 | 使用同一对凭据、同步系统时间、`us-east-1`、Path Style；不要改写 Host |
| `NoSuchBucket` | Bucket 是否真的存在 | 在 MinIO 创建桶，填写精确桶名；Endpoint 不拼接桶名 |
| `AccessDenied` | 凭据对目标桶是否有对应操作权限 | 区分健康访问、列桶、读、写权限，按应用所需授权 |
| HTTP 413 / 大文件中断 | 代理请求大小、超时、SDK 分片大小 | 阅读 Cloudflare 当前限制，调整分片并实际验证；不能保证所有平台适配 |
| HTTP 429 | 临时隧道并发限制 | 降低并发或换适合持续服务的入口 |
| 修改账户后第三方失败 | 进程是否重启，应用是否仍用旧密钥 | 停启 MinIO，更新成对凭据并重新测试 |
| 重启电脑后服务没有启动 | 尚未登录、任务用户不匹配、脚本路径变化 | 本方案是用户登录任务；查看任务计划程序与日志 |

## 不输出密码的检查命令

以下命令默认安装在 `E:\MinIO`，普通 PowerShell 即可执行：

```powershell
& E:\MinIO\Status-MinIO.ps1
Get-Content E:\MinIO\config\https-certificate-info.json
Get-ScheduledTaskInfo -TaskName MinIO-Local-E
Get-ChildItem E:\MinIO\logs -File | Sort-Object LastWriteTime -Descending | Select-Object -First 6 Name,Length,LastWriteTime
```

查看具体日志时使用 `Get-Content -Tail 60 '完整日志路径'`。向别人发送日志前检查其中是否包含实际地址、对象名或其他敏感信息。不要读取或发送 `credentials.xml`、`private.key`、`https-ca-private.key`。

## 证书续期或内网 IP 变化

首次生成器会拒绝覆盖已有证书，这是有意的保护。正常续期应保留原 CA，在包含新 SAN 的服务端证书上重新签名，再替换服务端证书和私钥并重启；客户端无需因普通叶子证书续期更换根 CA。此仓库没有实现这套续期工具。

如果选择在新的空目录生成一整套 CA 和服务端证书，必须备份原配置，替换时停启服务，并更新 cloudflared 的 CA 文件，以及每个直连客户端的信任。**不要只替换其中一个证书或私钥，也不要删除 data。** 发布或提交时同样不能包含新私钥。

## 关于停止与备份

`Stop-MinIO.ps1` 只处理可执行路径匹配这套部署的进程，但属于 Windows 进程停止操作，执行前应暂停上传和应用写入，避免在传输中停机。备份文件数据时保留整个数据目录结构；不要随意修改内部 `.minio.sys`。单机单盘不提供磁盘故障冗余，应另行安排备份。

参见：[手动教程](manual-guide.md) · [连接参数](../examples/connection.md)
