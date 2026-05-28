import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, message, Popconfirm, Tag, Space, Typography, Card, Row, Col, Statistic, Descriptions, Progress, Tabs, Switch, Empty } from 'antd';
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, EyeOutlined, BankOutlined, TeamOutlined, UserOutlined, AlertOutlined, FileTextOutlined, KeyOutlined, LoginOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { enterSchool } from '../../api/auth';
import { useAuthStore } from '../../stores/authStore';

const riskLabels: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险', urgent: '紧急风险' };
const riskColors: Record<string, string> = { low: '#1890FF', medium: '#FA8C16', high: '#FF4D4F', urgent: '#CF1322' };

export default function SchoolManagement() {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [admins, setAdmins] = useState<any[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<any>(null);
  const [enteringSchool, setEnteringSchool] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [resetForm] = Form.useForm();
  const setAuth = useAuthStore(s => s.setAuth);
  const savePlatformSession = useAuthStore(s => s.savePlatformSession);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const r = await client.get('/platform/schools', { params: { page, page_size: 20 } });
      setData(r.data.data.items); setTotal(r.data.data.total);
    } catch { message.error('获取学校列表失败'); }
    finally { setLoading(false); }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ create_admin: true });
    setModalOpen(true);
  };
  const openEdit = (s: any) => { setEditing(s); form.setFieldsValue(s); setModalOpen(true); };

  const viewDetail = async (s: any) => {
    setDetailLoading(true); setDetail(null); setAdmins([]); setDetailOpen(true);
    try {
      const [detailRes, adminRes] = await Promise.all([
        client.get(`/platform/schools/${s.id}`),
        client.get(`/platform/schools/${s.id}/admins`),
      ]);
      setDetail(detailRes.data.data);
      setAdmins(adminRes.data.data || []);
    }
    catch { message.error('获取学校详情失败'); }
    finally { setDetailLoading(false); }
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) { await client.put(`/platform/schools/${editing.id}`, values); message.success('更新成功'); }
      else { await client.post('/platform/schools', values); message.success('学校创建成功'); }
      setModalOpen(false); fetchData();
    } catch (err: any) { message.error(err?.response?.data?.detail || '操作失败'); }
  };

  const handleEnterSchool = async (schoolId: number) => {
    setEnteringSchool(schoolId);
    try {
      const school = data.find((s: any) => s.id === schoolId);
      savePlatformSession();
      if (school) {
        localStorage.setItem('platform_school_name', school.name);
      }
      const result = await enterSchool(schoolId);
      // 直接写 localStorage，不用 setAuth 避免触发当前页面重渲染导致 403
      localStorage.setItem('user', JSON.stringify(result.user));
      localStorage.setItem('access_token', result.access_token);
      message.success('已切换到学校视角');
      window.location.replace('/school-admin/dashboard');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '进入失败');
    } finally {
      setEnteringSchool(null);
    }
  };

  const toggleStatus = async (s: any) => {
    if (s.status) {
      await client.delete(`/platform/schools/${s.id}`); message.success('已停用');
    } else {
      await client.post(`/platform/schools/${s.id}/enable`); message.success('已启用');
    }
    fetchData();
  };

  const openReset = (admin: any) => {
    setResetTarget(admin);
    resetForm.resetFields();
    setResetOpen(true);
  };

  const handleResetPassword = async () => {
    const values = await resetForm.validateFields();
    await client.post(`/platform/schools/${detail.id}/admins/${resetTarget.id}/reset-password`, values);
    message.success('密码已重置，该账号下次登录需修改密码');
    setResetOpen(false);
  };

  const disableAdmin = async (admin: any) => {
    await client.post(`/platform/schools/${detail.id}/admins/${admin.id}/disable`);
    message.success('学校管理员账号已停用');
    viewDetail(detail);
  };

  const columns = [
    { title: '学校名称', dataIndex: 'name', key: 'name', render: (v: string, r: any) => <a onClick={() => viewDetail(r)}>{v}</a> },
    { title: '编码', dataIndex: 'code', key: 'code', width: 100 },
    { title: '管理员', dataIndex: 'admin_name', key: 'admin_name', width: 100 },
    { title: '学生', dataIndex: 'student_count', key: 'student_count', width: 60, align: 'right' as const },
    { title: '教师', dataIndex: 'teacher_count', key: 'teacher_count', width: 60, align: 'right' as const },
    { title: '状态', dataIndex: 'status', key: 'status', width: 70, render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '正常' : '停用'}</Tag> },
    { title: '操作', key: 'action', width: 380, render: (_: any, r: any) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => viewDetail(r)}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Button size="small" icon={<LoginOutlined />} loading={enteringSchool === r.id} onClick={() => handleEnterSchool(r.id)}
            style={{ color: '#1677ff', borderColor: '#1677ff' }}>进入后台</Button>
          <Popconfirm title={r.status ? '确定停用该学校？' : '确定启用该学校？'} onConfirm={() => toggleStatus(r)}>
            <Button size="small" icon={r.status ? <StopOutlined /> : <CheckCircleOutlined />} danger={r.status}>
              {r.status ? '停用' : '启用'}
            </Button>
          </Popconfirm>
        </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4}>学校管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增学校</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 所学校` }} />

      {/* 编辑弹窗 */}
      <Modal title={editing ? '编辑学校' : '新增学校'} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} width={520} destroyOnHidden>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="学校名称" rules={[{ required: true }]}><Input placeholder="如：明德实验学校" /></Form.Item>
          <Form.Item name="code" label="学校编码" rules={[{ required: true }]}><Input placeholder="如：MINGDE" disabled={!!editing} /></Form.Item>
          <Form.Item name="address" label="地址"><Input /></Form.Item>
          <Form.Item name="phone" label="联系电话"><Input /></Form.Item>
          {!editing && <>
            <Form.Item name="create_admin" label="同步创建学校管理员" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item shouldUpdate noStyle>
              {({ getFieldValue }) => getFieldValue('create_admin') !== false && (
                <>
                  <Form.Item name="admin_username" label="管理员账号" rules={[{ required: true, message: '请输入管理员账号' }]}>
                    <Input placeholder="如：admin_mingde" />
                  </Form.Item>
                  <Form.Item name="admin_password" label="初始密码" rules={[{ required: true, min: 10, message: '初始密码至少10位' }]}>
                    <Input.Password placeholder="请设置至少10位初始密码" />
                  </Form.Item>
                  <Form.Item name="admin_name" label="管理员姓名" rules={[{ required: true, message: '请输入管理员姓名' }]}>
                    <Input placeholder="如：学校管理员" />
                  </Form.Item>
                  <Form.Item name="admin_phone" label="管理员手机号">
                    <Input placeholder="用于账号通知，可留空" />
                  </Form.Item>
                </>
              )}
            </Form.Item>
          </>}
        </Form>
      </Modal>

      {/* 详情弹窗 */}
      <Modal title={detail ? `${detail.name} - 详细信息` : '学校详情'} open={detailOpen} onCancel={() => setDetailOpen(false)} width={800} footer={null} destroyOnHidden>
        {detailLoading ? <Typography.Text>加载中...</Typography.Text> : detail ? (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={4}><Statistic title="学生" value={detail.student_count} prefix={<TeamOutlined />} /></Col>
              <Col span={4}><Statistic title="教师" value={detail.teacher_count} prefix={<UserOutlined />} /></Col>
              <Col span={4}><Statistic title="班级" value={detail.class_count} prefix={<BankOutlined />} /></Col>
              <Col span={4}><Statistic title="任务" value={detail.task_count} prefix={<FileTextOutlined />} /></Col>
              <Col span={4}><Statistic title="答卷" value={detail.answer_sheet_count || 0} /></Col>
              <Col span={4}><Statistic title="预警" value={detail.risk_count} prefix={<AlertOutlined />} valueStyle={{ color: '#FF4D4F' }} /></Col>
            </Row>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={4}><Statistic title="待处理" value={detail.pending_risks} valueStyle={{ color: '#FA8C16' }} /></Col>
              <Col span={4}><Statistic title="完成率" value={detail.metrics?.completion_rate || 0} suffix="%" /></Col>
              <Col span={4}><Statistic title="干预完成率" value={detail.metrics?.intervention_completion_rate || 0} suffix="%" /></Col>
            </Row>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="学校名称">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="编码">{detail.code}</Descriptions.Item>
              <Descriptions.Item label="管理员">{detail.admin_name} ({detail.admin_username})</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={detail.status ? 'green' : 'red'}>{detail.status ? '正常' : '停用'}</Tag></Descriptions.Item>
              <Descriptions.Item label="地址">{detail.address || '-'}</Descriptions.Item>
              <Descriptions.Item label="电话">{detail.phone || '-'}</Descriptions.Item>
            </Descriptions>
            <Card title="学校管理员账号" size="small" style={{ marginTop: 16 }}>
              <Table
                rowKey="id"
                dataSource={admins}
                pagination={false}
                size="small"
                locale={{ emptyText: <Empty description="暂无学校管理员账号" /> }}
                columns={[
                  { title: '账号', dataIndex: 'username' },
                  { title: '姓名', dataIndex: 'real_name' },
                  { title: '手机号', dataIndex: 'phone', render: (v: string) => v || '-' },
                  { title: '状态', dataIndex: 'status', render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag> },
                  { title: '首次改密', dataIndex: 'must_change_password', render: (v: boolean) => v ? <Tag color="orange">待修改</Tag> : <Tag color="green">已处理</Tag> },
                  { title: '最近登录', dataIndex: 'last_login_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                  {
                    title: '操作',
                    width: 160,
                    render: (_: any, admin: any) => (
                      <Space>
                        <Button size="small" icon={<KeyOutlined />} onClick={() => openReset(admin)}>重置密码</Button>
                        {admin.status && (
                          <Popconfirm title="确定停用该学校管理员账号？" onConfirm={() => disableAdmin(admin)}>
                            <Button size="small" danger>停用</Button>
                          </Popconfirm>
                        )}
                      </Space>
                    ),
                  },
                ]}
              />
            </Card>
            <Card title="风险分布" size="small" style={{ marginTop: 16 }}>
              {detail.risk_distribution && Object.keys(detail.risk_distribution).length > 0 ? (
                Object.entries(detail.risk_distribution).map(([level, count]) => {
                  const total = detail.risk_count || 1;
                  const pct = Math.round((count as number) / total * 100);
                  return (
                    <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <Tag color={riskColors[level]}>{riskLabels[level]}</Tag>
                      <Progress percent={pct} size="small" style={{ flex: 1 }} strokeColor={riskColors[level]} />
                      <span>{count as number}人</span>
                    </div>
                  );
                })
              ) : <Typography.Text type="secondary">暂无风险数据</Typography.Text>}
            </Card>
            <Card title="年级概况" size="small" style={{ marginTop: 16 }}>
              <Table rowKey="name" dataSource={detail.grades || []} pagination={false} size="small"
                columns={[
                  { title: '年级', dataIndex: 'name' },
                  { title: '学生数', dataIndex: 'students' },
                  { title: '班级数', dataIndex: 'classes' },
                ]} />
            </Card>
            <Card title="最近使用情况" size="small" style={{ marginTop: 16 }}>
              <Tabs
                items={[
                  {
                    key: 'tasks',
                    label: '最近任务',
                    children: (
                      <Table
                        rowKey="id"
                        dataSource={detail.recent_tasks || []}
                        pagination={false}
                        size="small"
                        locale={{ emptyText: <Empty description="暂无最近任务" /> }}
                        columns={[
                          { title: '任务名称', dataIndex: 'name' },
                          { title: '状态', dataIndex: 'status', render: (v: string) => <Tag>{v}</Tag> },
                          { title: '更新时间', dataIndex: 'updated_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                        ]}
                      />
                    ),
                  },
                  {
                    key: 'logins',
                    label: '最近登录',
                    children: (
                      <Table
                        rowKey={(record: any) => `${record.username}-${record.login_time}`}
                        dataSource={detail.recent_logins || []}
                        pagination={false}
                        size="small"
                        locale={{ emptyText: <Empty description="暂无登录记录" /> }}
                        columns={[
                          { title: '账号', dataIndex: 'username' },
                          { title: '角色', dataIndex: 'role' },
                          { title: '登录时间', dataIndex: 'login_time', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                        ]}
                      />
                    ),
                  },
                  {
                    key: 'risks',
                    label: '最近风险处理',
                    children: (
                      <Table
                        rowKey="id"
                        dataSource={detail.recent_risk_updates || []}
                        pagination={false}
                        size="small"
                        locale={{ emptyText: <Empty description="暂无风险处理记录" /> }}
                        columns={[
                          { title: '风险提示ID', dataIndex: 'id' },
                          { title: '状态', dataIndex: 'status', render: (v: string) => <Tag>{v}</Tag> },
                          { title: '最近处理时间', dataIndex: 'latest_handled_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                        ]}
                      />
                    ),
                  },
                ]}
              />
            </Card>
          </div>
        ) : null}
      </Modal>
      <Modal
        title={`重置密码 - ${resetTarget?.real_name || ''}`}
        open={resetOpen}
        onOk={handleResetPassword}
        onCancel={() => setResetOpen(false)}
        destroyOnHidden
      >
        <Form form={resetForm} layout="vertical">
          <Form.Item name="password" label="新初始密码" rules={[{ required: true, min: 10, message: '新密码至少10位' }]}>
            <Input.Password placeholder="请输入至少10位新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
