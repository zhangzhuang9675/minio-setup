"""Draw reproducible Chinese tutorial diagrams, not simulated screenshots.

Requires Pillow; Windows Microsoft YaHei font, or pass MINIO_DIAGRAM_FONT.
"""
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'docs/assets'
FONT = os.environ.get('MINIO_DIAGRAM_FONT', 'C:/Windows/Fonts/msyh.ttc')
W = 1600
NAVY, TEXT, MUTED = '#102A43', '#243B53', '#52677D'
BLUE, GREEN, BG = '#2365C5', '#167D67', '#F0F5FA'


def font(size):
    return ImageFont.truetype(FONT, size)


def canvas(title, subtitle, height=980):
    im = Image.new('RGB', (W, height), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 172), fill=NAVY)
    d.text((64, 34), title, font=font(44), fill='white')
    d.text((66, 107), subtitle, font=font(24), fill='#C6D9EC')
    d.text((64, height-45), 'MINIO SETUP  /  自绘示意图 · 示例地址需替换 · 2026-09', font=font(20), fill=MUTED)
    return im, d


def text(d, xy, value, size=27, color=TEXT, width=None):
    x, y = xy
    for line in value.split('\n'):
        if width is not None:
            assert d.textlength(line, font=font(size)) <= width, (value, width)
        d.text((x, y), line, font=font(size), fill=color)
        y += int(size*1.65)
    return y


def box(d, rect, title, body, accent=BLUE, size=26):
    x, y, r, b = rect
    d.rounded_rectangle(rect, radius=20, fill='white', outline='#D4E0EC', width=2)
    d.rounded_rectangle((x, y, x+8, b), radius=4, fill=accent)
    text(d, (x+26, y+22), title, 31, accent, r-x-50)
    last = text(d, (x+26, y+83), body, size, TEXT, r-x-50)
    assert last < b+12, (title, last, b)


def arrow(d, start, end, color=BLUE):
    x, y = end
    d.line((start, end), fill=color, width=5)
    if start[1] == y:
        d.polygon([(x,y),(x-17,y-10),(x-17,y+10)],fill=color)
    else:
        d.polygon([(x,y),(x-10,y-17),(x+10,y-17)],fill=color)


def save(im, name):
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / name, optimize=True)
    print(name, im.size)


im,d = canvas('跨网络访问：从第三方程序到 E 盘', '无需路由器端口转发；对方不必安装客户端。公共入口只接入 S3 API。')
box(d,(64,220,485,460),'① 其他网络的程序','填写当前公共 HTTPS 地址\n使用 S3 凭据访问桶\n例如：Bucket = test')
box(d,(560,220,1040,460),'② Cloudflare 公共入口','https://your-tunnel\n.trycloudflare.com\n示例域名 · 公共受信任证书')
box(d,(1115,220,1536,460),'③ 本机 cloudflared','由本机主动建立隧道\nHTTP/2 · 出站 TCP 7844\n校验本地 CA 与 localhost',size=24)
arrow(d,(490,340),(552,340)); arrow(d,(1045,340),(1107,340))
arrow(d,(1325,470),(1325,570))
text(d,(810,497),'源站 HTTPS  →  127.0.0.1:9000',25,GREEN)
box(d,(920,580,1536,800),'④ 本机 MinIO → E 盘文件','S3 API：9000\n数据目录：E:\\MinIO\\data',GREEN)
box(d,(64,580,840,800),'本机管理页面：单独使用 9001','浏览器打开 https://127.0.0.1:9001\n仅本机监听，不是第三方程序的 Endpoint',BLUE)
text(d,(66,847),'请求路径示意；TLS 在 Cloudflare 终止后再转发。隧道重建可能换域名。',27,MUTED)
save(im,'architecture.png')

im,d=canvas('手动部署路线：按顺序完成 6 个阶段','每一步都有明确的完成判断；先本机成功，再验证跨网络访问。',990)
cards=[('01  准备 E 盘','下载教程，建立目录\n记录正在使用的内网 IP'),('02  构建 MinIO','下载 Go 并核验 SHA-256\n编译固定版本到 bin'),('03  凭据与证书','加密保存账户和密码\n生成证书并信任本地 CA'),('04  启动与存储','HTTPS 健康检查返回 200\n创建桶，上传下载并比较'),('05  公共隧道','下载并校验 cloudflared\n启动后读取实际 HTTPS 域名'),('06  填写与验收','填入桶名、地址和成对凭据\n用第三方程序完成真实读写')]
for i,(title,body) in enumerate(cards):
    col,row=i%3,i//3
    x,y=64+col*505,220+row*310
    box(d,(x,y,x+460,y+240),title,body,GREEN if i==5 else BLUE,size=24)
text(d,(68,862),'已有部署：直接查看教程中的日常管理与连接步骤，不要重新覆盖证书或数据。',25,MUTED)
save(im,'roadmap.png')

im,d=canvas('文件放在哪里：主要空间留在 E 盘','安装目录 E:\\MinIO；Windows 和浏览器仍可能使用少量系统盘空间。',1080)
rows=[('bin / tools','MinIO、Go、Python 等工具','留在本机'),('data','桶、对象及 MinIO 内部元数据','业务数据，需备份'),('logs / tmp / build','运行日志、临时文件、构建缓存','留在 E 盘'),('config','加密凭据、CA 私钥、证书元信息','敏感，不公开'),('certs','服务端证书 public.crt + 私钥 private.key','私钥，不发送'),('client-certs','minio-root-ca.crt：根 CA 公共证书','内网客户端可导入'),('tunnel','cloudflared.exe 和当前隧道状态','在线地址不写入教程')]
for i,(a,b,c) in enumerate(rows):
    y=215+i*104
    d.rounded_rectangle((64,y,1536,y+88),radius=12,fill='white')
    text(d,(88,y+25),a,27,BLUE,290)
    text(d,(390,y+25),b,25,TEXT,720)
    text(d,(1180,y+25),c,23,GREEN if i==5 else MUTED,335)
save(im,'directories.png')

im,d=canvas('HTTPS 怎么被信任：两条路径分开看','加密、证书信任和网络可达性是三个条件，缺少任意一个都可能连接失败。',1100)
text(d,(65,207),'A  同一内网直连',33,BLUE)
box(d,(64,275,530,485),'客户端程序','访问内网 IP:9000\n需要信任本地 CA',BLUE)
box(d,(690,275,1536,485),'MinIO 原生 HTTPS','证书 SAN 必须包含访问使用的内网 IP\n程序可能使用自己的 CA 存储，不一定跟随浏览器',BLUE)
arrow(d,(540,380),(680,380))
text(d,(65,548),'B  其他网络通过公共隧道访问',33,GREEN)
box(d,(64,615,505,830),'外部程序','信任公共 CA\n通常无需安装你的本地 CA',GREEN,size=23)
box(d,(575,615,1025,830),'Cloudflare → 隧道客户端','公共证书对外服务\n本机主动连接 Cloudflare',GREEN,size=23)
box(d,(1095,615,1536,830),'本机 MinIO','cloudflared 使用本地 CA\n校验源站 HTTPS 证书',GREEN,size=23)
arrow(d,(513,720),(567,720),GREEN);arrow(d,(1033,720),(1087,720),GREEN)
text(d,(66,914),'可以给客户端：minio-root-ca.crt（公共证书）',28,GREEN)
text(d,(66,965),'不能给客户端：private.key、https-ca-private.key（私钥）',28,'#B13E38')
save(im,'https-trust.png')

im,d=canvas('第三方 S3 配置：四个必填值', '字段示意图，非产品截图。先创建桶，再把当前地址和同一对凭据填入。',1110)
fields=[('1  Bucket','test','填写实际桶名；这是示例桶。'),('2  Endpoint','https://your-tunnel.trycloudflare.com','替换为本次分配的真实域名，不加桶名或 :9001。'),('3  AccessKeyId','你设置的 MinIO 用户名 / 专用访问密钥 ID','不是 GitHub 或 Windows 账号。'),('4  SecretAccessKey','与上一项配套的密码 / 访问密钥 Secret','成对填写；不要使用图片中的文字作为密码。')]
for i,(label,value,hint) in enumerate(fields):
    y=206+i*175
    text(d,(68,y),label,28,BLUE)
    d.rounded_rectangle((64,y+49,1536,y+112),radius=10,fill='white',outline='#B4C8DC',width=2)
    text(d,(86,y+59),value,28,TEXT,1420)
    text(d,(87,y+120),hint,21,MUTED,1410)
d.rounded_rectangle((64,933,1536,1026),radius=14,fill='#DFEEE8')
text(d,(88,958),'Region：us-east-1     |     Virtual Host：不勾选（Path Style）',29,GREEN,1400)
save(im,'connection-form.png')
