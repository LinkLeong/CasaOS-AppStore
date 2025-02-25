import sys
import yaml
import requests
import re

def get_latest_version(image, strategy):
    repo = image.split(':')[0]
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags/?page_size=100"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, str(e)
    
    tags = response.json().get('results', [])
    
    if strategy == 'latest':
        for tag in tags:
            if tag['name'] == 'latest':
                return 'latest', None
        return None, "未找到 'latest' 标签"
    elif strategy == 'semver':
        semver_tags = []
        pattern = re.compile(r'^\d+\.\d+\.\d+$')
        for tag in tags:
            if pattern.match(tag['name']):
                semver_tags.append(tag['name'])
        if not semver_tags:
            return None, "未找到语义化版本标签"
        sorted_tags = sorted(semver_tags, key=lambda x: tuple(map(int, x.split('.'))))
        return sorted_tags[-1], None
    else:
        return None, f"未知策略: {strategy}"


        



def send_notification(compose_file, service, image, current_version, latest_version, error=None):
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/fb911d9e-af1a-49ea-89b6-c514fc0c06ee"

    
    if error:
        markdown = f"""
        ### 🚨 服务检查失败 - {compose_file}
        ​**服务名称:**​ {service}  
        ​**镜像地址:**​ {image}  
        ​**当前版本:**​ {current_version}  
        ​**错误详情:**​ {error}
        """
    else:
        markdown = f"""
        ### ✅ 无需更新 - {compose_file}
        ​**服务名称:**​ {service}  
        ​**镜像地址:**​ {image}  
        ​**当前版本:**​ {current_version}  
        ​**最新版本:**​ {latest_version}
        """

       
    try:
        url = webhook_url
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        payload_message = {
            "msg_type": "text",
            "content": {markdown}
        }
        response = requests.post(url=url, data=json.dumps(payload_message), headers=headers)
        
        print(f"📢 通知已发送至飞书机器人")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 通知发送失败: {e}")

def main(compose_file, strategy):
    try:
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        send_notification(
            compose_file,
            "N/A",
            "N/A",
            "N/A",
            None,
            f"解析Compose文件失败: {e}"
        )
        return
    
    services = compose_data.get('services', {})
    
    for service, config in services.items():
        image = config.get('image')
        if not image:
            continue
        
        parts = image.split(':')
        if len(parts) == 2:
            repo, version = parts
        else:
            repo, version = image, 'latest'
        
        latest_version, error = get_latest_version(repo, strategy)
        update_needed = False
        
        if latest_version is not None:
            update_needed = (version != latest_version)
        else:
            update_needed = True
        
        print(f"🔍 检查服务: {service}/{image}")
        if latest_version is not None:
            print(f"  当前版本: {version}")
            print(f"  最新版本: {latest_version}")
            print(f"  需要更新: {'是' if update_needed else '否'}")
        else:
            print(f"  ❌ 发生错误: {error}")
            print(f"  需要更新: 是")
        
        with open('version_check.md', 'a') as report:
            report.write(f"## 📊 {compose_file} 版本检查结果\n")
            report.write(f"### 服务: {service}\n")
            report.write(f"- ​**镜像地址:**​ {image}\n")
            if latest_version is not None:
                report.write(f"- ​**当前版本:**​ {version}\n")
                report.write(f"- ​**最新版本:**​ {latest_version}\n")
                report.write(f"- ​**需要更新:**​ {'是' if update_needed else '否'}\n")
            else:
                report.write(f"- ​**错误信息:**​ {error}\n")
                report.write(f"- ​**需要更新:**​ 是\n\n")
        
        if latest_version is None or not update_needed:
            send_notification(
                compose_file,
                service,
                image,
                version,
                latest_version,
                error
            )

if __name__ == "__main__":
    compose_file = sys.argv[1]
    strategy = sys.argv[2]
    main(compose_file, strategy)
