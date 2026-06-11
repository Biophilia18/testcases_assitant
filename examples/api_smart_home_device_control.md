# 智控家监测系统接口文档

## 项目/系统名称：智控家监测系统
## 业务模块：基础设备控制
## 接口名称：设备控制接口
## 请求方法：POST
## 接口路径：/api/devices/{deviceId}/control
## 鉴权方式：Bearer Token

## 请求头：
- Authorization: Bearer ${token}
- Content-Type: application/json

## 请求参数：
- deviceId：设备ID，路径参数，必填，integer，大于0，必须存在，必须属于当前用户

## 请求体：
```json
{
  "action": "open",
  "mode": "auto"
}
```

## 字段说明：
- action：控制动作，必填，string，允许值 open、close、switch_mode
- mode：工作模式，action为switch_mode时必填，string，允许值 auto、manual

## 成功响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "deviceId": "10001",
    "status": "open"
  }
}
```

## 失败响应：
```json
{
  "code": 400,
  "message": "device offline"
}
```

## 业务规则：
- 设备必须在线才允许控制
- 用户必须已经绑定该设备
- 用户无设备权限时不能执行控制操作
- 重复点击控制按钮不能重复发送大量控制请求
- 服务端返回异常状态码时页面需要给出明确提示

## 数据库校验：
- 设备状态记录更新
- 控制日志写入
- 操作用户ID、设备ID、控制动作与请求一致
