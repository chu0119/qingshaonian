import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Select, DatePicker, Typography, message, Space } from 'antd';
import type { Dayjs } from 'dayjs';
import client from '../../api/client';
import { ROLE_LABELS, RESULT_LABELS } from '../../utils/constants';

const moduleLabels: Record<string, string> = {
  auth: '认证', user: '用户', student: '学生', teacher: '教师',
  questionnaire: '问卷', questionnaire_task: '任务管理',
  task: '任务', risk: '风险', risk_alert: '风险预警',
  intervention: '干预', report: '报表',
  system: '系统', sms: '短信', ai_analysis: 'AI分析',
  quality: '质量检测', audit: '审计', platform: '平台', school: '学校',
  class: '班级', export: '导出',
  platform_school: '学校管理', platform_supervision: '监管督办',
};

const actionLabels: Record<string, string> = {
  login: '登录',
  logout: '登出',
  view: '查看',
  view_detail: '查看详情',
  create: '创建',
  update: '更新',
  delete: '删除',
  export: '导出',
  import: '导入',
  send: '发送',
  disable: '停用',
  enable: '启用',
  force_delete: '彻底删除',
  reset_password: '重置密码',
  change_password: '修改密码',
  assign_classes: '分配班级',
  send_code: '发送验证码',
  publish: '发布',
  close: '关闭',
  extend: '延期',
  archive: '归档',
  recall: '撤回',
  analyze: '分析',
  send_business: '发送',
  retry: '重试',
  change_class: '调整班级',
  view_profile: '查看档案',
  export_students: '导出学生',
  urge_intervention: '督促处理',
  remind: '发送提醒',
  update_school_info: '更新学校信息',
  update_risk_config: '更新风险配置',
  update_sms_config: '更新短信配置',
  update_screen_config: '更新大屏配置',
  create_grade: '创建年级',
  delete_grade: '删除年级',
  seed_demo_data: '初始化演示数据',
  regional_analysis: '区域分析',
  enter_school: '进入学校',
};

const objectTypeLabels: Record<string, string> = {
  user: '用户',
  student: '学生',
  teacher: '教师',
  school: '学校',
  class: '班级',
  grade: '年级',
  questionnaire: '问卷',
  task: '任务',
  risk_alert: '风险预警',
  risk_alerts: '风险预警',
  intervention: '干预记录',
  answer_sheet: '答卷',
  sms_log: '短信记录',
  sms: '短信',
  report: '报告',
  config: '配置',
  phone: '手机号',
  student_list: '学生列表',
  student_batch: '学生批次',
  platform_admin: '平台管理员',
  audit: '审计',
};

const actionOptions = Object.entries(actionLabels).map(([k, v]) => ({ value: k, label: v }));

const { RangePicker } = DatePicker;

export default function SchoolAuditLogs() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState('');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (action) params.action = action;
      if (dateRange && dateRange[0]) params.start_date = dateRange[0].format('YYYY-MM-DD');
      if (dateRange && dateRange[1]) params.end_date = dateRange[1].format('YYYY-MM-DD');
      const r = await client.get('/reports/audit-logs', { params });
      setData(r.data.data.items || []);
      setTotal(r.data.data.total || 0);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取审计日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, action, dateRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    {
      title: '时间',
      dataIndex: 'operation_time',
      key: 'operation_time',
      width: 170,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作人',
      dataIndex: 'operator_name',
      key: 'operator_name',
      width: 120,
      render: (v: string) => v || '-',
    },
    {
      title: '角色',
      dataIndex: 'operator_role',
      key: 'operator_role',
      width: 110,
      render: (v: string) => <Tag>{ROLE_LABELS[v] || '未知'}</Tag>,
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 100,
      render: (v: string) => <Tag>{moduleLabels[v] || '-'}</Tag>,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (v: string) => actionLabels[v] || '-',
    },
    {
      title: '对象',
      dataIndex: 'object_name',
      key: 'object_name',
      width: 150,
      render: (v: string, r: any) => {
        const parts: string[] = [];
        if (r.object_type) parts.push(objectTypeLabels[r.object_type] || r.object_type);
        if (v) parts.push(v);
        return parts.length > 0 ? parts.join(' / ') : '-';
      },
    },
    {
      title: 'IP',
      dataIndex: 'request_ip',
      key: 'request_ip',
      width: 130,
      render: (v: string) => v || '-',
    },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 70,
      render: (v: string) => {
        const color = v === 'success' ? 'green' : v === 'failure' ? 'red' : 'default';
        return <Tag color={color}>{RESULT_LABELS[v] || '-'}</Tag>;
      },
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>操作日志</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="操作类型"
          allowClear
          style={{ width: 130 }}
          value={action || undefined}
          onChange={v => { setAction(v || ''); setPage(1); }}
          options={actionOptions}
        />
        <RangePicker
          value={dateRange}
          onChange={dates => { setDateRange(dates as [Dayjs | null, Dayjs | null] | null); setPage(1); }}
          placeholder={['开始日期', '结束日期']}
        />
      </Space>
      <Table
        rowKey="id"
        dataSource={data}
        columns={columns}
        loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }}
      />
    </div>
  );
}
