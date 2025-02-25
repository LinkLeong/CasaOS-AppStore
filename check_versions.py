import sys
import yaml
import requests
import re

def get_latest_version(image, strategy):
    # 从镜像名称中提取仓库部分（去掉版本）
    repo = image.split(':')[0]
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags/?page_size=100"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    tags = response.json()['results']
    
    if strategy == 'latest':
        for tag in tags:
            if tag['name'] == 'latest':
                return 'latest'
        return None
    elif strategy == 'semver':
        # 筛选语义化版本（如 1.2.3）
        semver_tags = [tag['name'] for tag in tags if re.match(r'^\d+\.\d+\.\d+$', tag['name'])]
        if semver_tags:
            return max(semver_tags, key=lambda x: [int(part) for part in x.split('.')])
        return None
    return None

def main(compose_file, strategy):
    # 读取并解析 Compose 文件
    with open(compose_file, 'r') as f:
        compose_data = yaml.safe_load(f)
    services = compose_data.get('services', {})
    
    # 处理每个服务
    for service, config in services.items():
        image = config.get('image')
        if image:
            # 分离镜像名称和版本
            parts = image.split(':')
            if len(parts) == 2:
                repo, version = parts
            else:
                repo, version = image, 'latest'  # 未指定版本时默认为 latest
            
            # 获取 Docker Hub 最新版本
            latest_version = get_latest_version(repo, strategy)
            if latest_version:
                update_needed = version != latest_version
                # 输出到控制台
                print(f"检查 {compose_file}")
                print(f"服务: {service}")
                print(f"  镜像: {image}")
                print(f"  最新版本: {latest_version}")
                print(f"  需要更新: {'是' if update_needed else '否'}")
                # 写入报告文件
                with open('version_check.md', 'a') as report:
                    report.write(f"### 检查 {compose_file}\n")
                    report.write(f"**服务:** {service}\n")
                    report.write(f"- **镜像:** {image}\n")
                    report.write(f"- **最新版本:** {latest_version}\n")
                    report.write(f"- **需要更新:** {'是' if update_needed else '否'}\n\n")

if __name__ == "__main__":
    compose_file = sys.argv[1]  # Compose 文件路径
    strategy = sys.argv[2]      # 最新版本策略
    main(compose_file, strategy)
