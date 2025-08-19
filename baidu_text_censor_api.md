# 百度AI文本审核接口文档

## 接口概述

百度AI文本审核接口提供智能文本内容安全检测服务，能够识别文本中的不良信息，包括但不限于违法违规、低俗、广告等内容。

## 接口地址

```
POST https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined
```

## 请求参数

### URL参数
- `access_token`: 通过API Key和Secret Key获取的访问令牌

### Body参数（form-data格式）
- `text`: 待检测的文本内容

## 鉴权方式

使用Access Token进行鉴权，需要先通过API Key和Secret Key获取Access Token。

## 代码示例

### C++示例

```cpp
#include <iostream>
#include <curl/curl.h>

static std::string TextCensor_result;

static size_t callback(void *data, size_t size, size_t nmemb, void *userp) {
    std::string *str = (std::string*)userp;
    str->append((char*)data, size * nmemb);
    return size * nmemb;
}

/**
 * 文本审核接口
 * @return 调用成功返回0，发生错误返回其他错误码
 */
int TextCensor(std::string &json_result, const std::string &access_token) {
    std::string url = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined?access_token=" + access_token;
    CURL *curl = NULL;
    CURLcode result_code;
    int is_success;
    curl = curl_easy_init();
    if (curl) {
        curl_easy_setopt(curl, CURLOPT_URL, url.data());
        curl_easy_setopt(curl, CURLOPT_POST, 1);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
        curl_httppost *post = NULL;
        curl_httppost *last = NULL;
        curl_formadd(&post, &last, CURLFORM_COPYNAME, "text", CURLFORM_COPYCONTENTS, "待检测的文本内容", CURLFORM_END);

        curl_easy_setopt(curl, CURLOPT_HTTPPOST, post);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, callback);
        result_code = curl_easy_perform(curl);
        if (result_code != CURLE_OK) {
            fprintf(stderr, "curl_easy_perform() failed: %s\n",
                    curl_easy_strerror(result_code));
            is_success = 1;
            return is_success;
        }
        json_result = TextCensor_result;
        curl_easy_cleanup(curl);
        is_success = 0;
    } else {
        fprintf(stderr, "curl_easy_init() failed.");
        is_success = 1;
    }
    return is_success;
}
```

### C#示例

```csharp
using System;
using System.IO;
using System.Net;
using System.Text;
using System.Web;

namespace com.baidu.ai
{
    public class TextCensor
    {
        // 文本审核接口
        public static string TextCensor()
        {
            string token = "[调用鉴权接口获取的token]";
            string host = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined?access_token=" + token;
            Encoding encoding = Encoding.Default;
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(host);
            request.Method = "post";
            request.KeepAlive = true;
            String str = "text=" + "待检测的文本内容";
            byte[] buffer = encoding.GetBytes(str);
            request.ContentLength = buffer.Length;
            request.GetRequestStream().Write(buffer, 0, buffer.Length);
            HttpWebResponse response = (HttpWebResponse)request.GetResponse();
            StreamReader reader = new StreamReader(response.GetResponseStream(), Encoding.Default);
            string result = reader.ReadToEnd();
            Console.WriteLine("文本审核接口:");
            Console.WriteLine(result);
            return result;
        }
    }
}
```

### Python示例

```python
import requests

def text_censor(text, access_token):
    """
    文本审核接口
    """
    url = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined"
    
    params = {
        'access_token': access_token
    }
    
    data = {
        'text': text
    }
    
    response = requests.post(url, params=params, data=data)
    return response.json()

# 使用示例
if __name__ == '__main__':
    access_token = "your_access_token_here"
    text_content = "待检测的文本内容"
    result = text_censor(text_content, access_token)
    print(result)
```

## 返回格式

接口返回JSON格式数据，包含审核结果和相关信息。

## 相关产品

- 音频内容安全
- 智能对话平台UNIT
- 曦灵智能数字人平台

## 技术支持

- **售前咨询**: 填写业务诉求，专属商务会联系您
- **售后工单**: 创建工单快捷反馈问题
- **联系销售**: 400-920-8999 转 1

## 参考文档

详细API文档请参考：[百度AI文本审核官方文档](https://ai.baidu.com/ai-doc/ANTIPORN/Rk3h6xb3i)
