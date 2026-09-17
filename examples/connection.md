# 第三方程序的填写模板

这些都是示例，不能原样复制域名和密码。请先在 MinIO 中创建桶。

| 字段 | 本机程序 | 同一内网的程序 | 其他网络的程序 |
| --- | --- | --- | --- |
| Bucket | `test`（实际桶名） | 同左 | 同左 |
| Endpoint | `https://127.0.0.1:9000` | `https://192.168.1.50:9000`（换成你的内网 IP） | `https://your-tunnel.trycloudflare.com`（换成当前隧道地址） |
| AccessKeyId | 你设置的 MinIO 用户名或专用访问密钥 ID | 同左 | 同左 |
| SecretAccessKey | 对应的 MinIO 密码或专用访问密钥 Secret | 同左 | 同左 |
| Region | `us-east-1` | `us-east-1` | `us-east-1` |
| Virtual Host | 不勾选，使用 Path Style | 不勾选 | 不勾选 |
| 证书信任 | 程序需要信任本地 CA | 程序需要信任本地 CA，IP 必须在证书 SAN 中 | 使用 Cloudflare 公共证书，通常系统已信任 |

Endpoint 不加桶名，不加 `/minio`，不用管理端口 `9001`。
如果输入框已经自动添加 `https://`，只填主机名（内网直连还要带 `:9000`），不要重复协议。
如果界面不能关闭 Virtual Host、不能设置 Region 或固定按某个云厂商签名，需要确认它是否支持通用 S3/MinIO。

首次连通性验证可使用部署时的管理员凭据。长期对接建议创建仅能操作目标桶的专用用户或访问密钥，并填写那一对凭据；不要把控制台登录密码与另一组访问密钥混搭。
