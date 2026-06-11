from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiExampleDocument:
    name: str
    text: str


API_EXAMPLE_DOCUMENTS = [
    ApiExampleDocument(
        name="爱家政：创建服务预约接口",
        text="""项目/系统名称：爱家政服务管理系统
业务模块：服务预约管理
接口名称：创建服务预约接口
请求方法：POST
接口路径：/api/appointments
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
Content-Type: application/json
请求参数：无
请求体：
{
  "serviceType": "cleaning",
  "serviceAddress": "上海市浦东新区示例路100号",
  "appointmentDate": "2026-06-10",
  "appointmentTime": "10:00",
  "contactName": "张三",
  "contactPhone": "13800000000",
  "remark": "需要提前电话联系"
}
字段说明：
serviceType：服务类型，必填，string，允许值 cleaning、repair、nanny
serviceAddress：服务地址，必填，string，长度1-200
appointmentDate：预约日期，必填，date，yyyy-MM-dd，不能早于当前日期
appointmentTime：预约时间，必填，string，格式HH:mm
contactName：联系人，必填，string，长度1-30
contactPhone：联系电话，必填，string，手机号格式
remark：备注，选填，string，长度0-200
成功响应：
{
  "code": 0,
  "message": "success",
  "data": {
    "appointmentNo": "YY202606100001",
    "status": "待派单"
  }
}
失败响应：
{
  "code": 400,
  "message": "appointment time invalid"
}
业务规则：
服务类型不能为空
预约时间不能早于当前时间
联系电话必须符合手机号格式
服务地址超出服务范围时不能提交预约
同一用户同一时间段不能重复预约相同服务
数据库校验：
预约主表生成预约记录
预约状态为待派单
预约编号唯一
联系人、联系电话、服务地址与请求内容一致
""",
    ),
    ApiExampleDocument(
        name="物资后勤：提交物资领用申请接口",
        text="""项目/系统名称：物资后勤管理系统
业务模块：物资领用申请
接口名称：提交物资领用申请接口
请求方法：POST
接口路径：/api/material/applications
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
Content-Type: application/json
请求参数：无
请求体：
{
  "materialId": 10001,
  "quantity": 5,
  "applyReason": "项目现场维修使用",
  "departmentId": 3001
}
字段说明：
materialId：物资ID，必填，integer，必须存在，必须属于当前用户可申请范围
quantity：领用数量，必填，integer，大于0，不能大于库存
applyReason：申请原因，必填，string，长度1-200
departmentId：申请部门ID，必填，integer，必须存在，必须属于当前用户
成功响应：
{
  "code": 0,
  "message": "success",
  "data": {
    "applicationNo": "WL202606090001",
    "status": "待审批"
  }
}
失败响应：
{
  "code": 400,
  "message": "quantity exceeds stock"
}
业务规则：
申请人必须属于申请部门
物资必须存在且处于可领用状态
领用数量不能大于当前库存
重复点击提交按钮不能生成多条申请单
无物资权限的用户不能提交申请
数据库校验：
物资申请主表生成申请记录
申请状态为待审批
库存不能被提前扣减
申请编号唯一
申请明细中的物资ID、数量、部门与请求内容一致
""",
    ),
    ApiExampleDocument(
        name="智控家：设备控制接口",
        text="""项目/系统名称：智控家监测系统
业务模块：基础设备控制
接口名称：设备控制接口
请求方法：POST
接口路径：/api/devices/{deviceId}/control
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
Content-Type: application/json
请求参数：
deviceId：设备ID，路径参数，必填，integer，大于0，必须存在，必须属于当前用户
请求体：
{
  "action": "open",
  "mode": "auto"
}
字段说明：
action：控制动作，必填，string，允许值 open、close、switch_mode
mode：工作模式，action为switch_mode时必填，string，允许值 auto、manual
成功响应：
{
  "code": 0,
  "message": "success",
  "data": {
    "deviceId": "10001",
    "status": "open"
  }
}
失败响应：
{
  "code": 400,
  "message": "device offline"
}
业务规则：
设备必须在线才允许控制
用户必须已经绑定该设备
用户无设备权限时不能执行控制操作
重复点击控制按钮不能重复发送大量控制请求
服务端返回异常状态码时页面需要给出明确提示
数据库校验：
设备状态记录更新
控制日志写入
操作用户ID、设备ID、控制动作与请求一致
""",
    ),
    ApiExampleDocument(
        name="爱家政：查询预约详情接口",
        text="""项目/系统名称：爱家政服务管理系统
业务模块：服务预约管理
接口名称：查询预约详情接口
请求方法：GET
接口路径：/api/appointments/{appointmentNo}
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
请求参数：
appointmentNo：预约编号，路径参数，必填，string，必须存在，必须属于当前用户
成功响应：
{
  "code": 0,
  "message": "success",
  "data": {
    "appointmentNo": "YY202606100001",
    "status": "待派单",
    "serviceType": "cleaning"
  }
}
失败响应：
{
  "code": 404,
  "message": "appointment not found"
}
业务规则：
用户只能查看自己的预约
不存在的预约编号返回明确错误
已取消的预约仍可查看详情但状态必须正确
数据库校验：
查询接口不应修改预约主表
返回的预约状态与数据库记录一致
""",
    ),
    ApiExampleDocument(
        name="爱家政：修改预约信息接口",
        text="""项目/系统名称：爱家政服务管理系统
业务模块：服务预约管理
接口名称：修改预约信息接口
请求方法：PUT
接口路径：/api/appointments/{appointmentNo}
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
Content-Type: application/json
请求参数：
appointmentNo：预约编号，路径参数，必填，string，必须存在，必须属于当前用户
请求体：
{
  "appointmentDate": "2026-06-11",
  "appointmentTime": "14:00",
  "contactPhone": "13800000000",
  "remark": "改到下午"
}
字段说明：
appointmentDate：预约日期，必填，date，yyyy-MM-dd，不能早于当前日期
appointmentTime：预约时间，必填，string，格式HH:mm
contactPhone：联系电话，必填，string，手机号格式
remark：备注，选填，string，长度0-200
成功响应：
{"code":0,"message":"success","data":{"appointmentNo":"YY202606100001","status":"待派单"}}
失败响应：
{"code":400,"message":"appointment cannot be modified"}
业务规则：
只有待派单状态的预约允许修改
用户只能修改自己的预约
预约时间不能早于当前时间
重复提交相同修改请求不能产生多条变更记录
数据库校验：
预约主表更新预约时间和联系方式
预约变更日志写入
""",
    ),
    ApiExampleDocument(
        name="智控家：更新告警状态接口",
        text="""项目/系统名称：智控家监测系统
业务模块：告警管理
接口名称：更新告警状态接口
请求方法：PATCH
接口路径：/api/alarms/{alarmId}/status
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
Content-Type: application/json
请求参数：
alarmId：告警ID，路径参数，必填，integer，大于0，必须存在，必须属于当前用户
请求体：
{"status":"processed","remark":"已处理"}
字段说明：
status：告警状态，必填，string，允许值 processed、ignored
remark：处理说明，选填，string，长度0-200
成功响应：
{"code":0,"message":"success","data":{"alarmId":10001,"status":"processed"}}
失败响应：
{"code":400,"message":"alarm status invalid"}
业务规则：
已处理的告警不能重复处理
用户只能处理自己权限范围内的设备告警
状态只能从待处理变更为已处理或已忽略
数据库校验：
告警状态更新
告警处理日志写入
""",
    ),
    ApiExampleDocument(
        name="物资后勤：删除草稿申请接口",
        text="""项目/系统名称：物资后勤管理系统
业务模块：物资领用申请
接口名称：删除草稿申请接口
请求方法：DELETE
接口路径：/api/material/applications/{applicationNo}
鉴权方式：Bearer Token
请求头：
Authorization: Bearer ${token}
请求参数：
applicationNo：申请编号，路径参数，必填，string，必须存在，必须属于当前用户
成功响应：
{"code":0,"message":"success"}
失败响应：
{"code":400,"message":"application status not draft"}
业务规则：
只有草稿状态的申请允许删除
用户只能删除自己创建的申请
已提交或已审批的申请不能删除
重复删除同一申请需要返回明确结果且不能产生异常数据
数据库校验：
草稿申请记录被逻辑删除
删除操作日志写入
已提交申请不会被删除
""",
    ),
]


API_EXAMPLE_BY_NAME = {example.name: example for example in API_EXAMPLE_DOCUMENTS}
