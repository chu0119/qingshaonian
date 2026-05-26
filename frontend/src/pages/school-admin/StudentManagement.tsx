import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Table, Button, Space, Tag, Modal, Form, Input, Select, message, Popconfirm, Upload,
  Row, Col, Card, Typography, Tooltip,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  UploadOutlined, DownloadOutlined, SearchOutlined,
  ReloadOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import {
  getStudents, createStudent, updateStudent,
  deleteStudent, importStudents, downloadTemplate,
  getDictGrades, type UserInfo,
} from '../../api/users';
import { getClasses, type ClassInfo } from '../../api/classes';

const { Title } = Typography;

export default function StudentManagement() {
  const [data, setData] = useState<UserInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    grade_id: undefined as number | undefined,
    class_id: undefined as number | undefined,
    keyword: '',
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState<UserInfo | null>(null);
  const [form] = Form.useForm();
  const [grades, setGrades] = useState<{ value: number; label: string }[]>([]);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [importing, setImporting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.grade_id) params.grade_id = filters.grade_id;
      if (filters.class_id) params.class_id = filters.class_id;
      if (filters.keyword) params.keyword = filters.keyword;
      const res = await getStudents(params);
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('获取学生列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  const fetchDicts = useCallback(async () => {
    try {
      const [gradeResults, classResults] = await Promise.all([
        getDictGrades(),
        getClasses({ page: 1, page_size: 200 }),
      ]);
      setGrades(gradeResults);
      setClasses(classResults.items);
    } catch {
      message.error('获取字典数据失败');
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    fetchDicts();
  }, [fetchDicts]);

  const openCreate = () => {
    setEditingStudent(null);
    form.resetFields();
    form.setFieldsValue({ status: true, gender: '男' });
    setModalOpen(true);
  };

  const openEdit = (record: UserInfo) => {
    setEditingStudent(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteStudent(id);
      message.success('删除成功');
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingStudent) {
        await updateStudent(editingStudent.id, values);
        message.success('更新成功');
      } else {
        await createStudent(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('操作失败');
    }
  };

  // 下载导入模板
  const handleDownloadTemplate = async () => {
    try {
      await downloadTemplate();
      message.success('模板下载成功');
    } catch {
      message.error('模板下载失败');
    }
  };

  // 批量导入 - 打开文件选择
  const handleImportClick = () => {
    inputRef.current?.click();
  };

  // 文件选择后上传
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 检查文件类型
    const validTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
    ];
    const validExt = file.name.endsWith('.xlsx') || file.name.endsWith('.xls');
    if (!validTypes.includes(file.type) && !validExt) {
      message.error('请选择 Excel 文件（.xlsx 或 .xls）');
      return;
    }

    setImporting(true);
    try {
      const result = await importStudents(file);
      if (result.fail_count > 0) {
        Modal.warning({
          title: '导入完成（有部分失败）',
          content: (
            <div>
              <p>成功导入 <strong style={{ color: '#52c41a' }}>{result.success_count}</strong> 条，
              失败 <strong style={{ color: '#ff4d4f' }}>{result.fail_count}</strong> 条</p>
              {result.errors && result.errors.length > 0 && (
                <div style={{
                  maxHeight: 200, overflow: 'auto', background: '#fff2f0',
                  padding: 12, borderRadius: 6, marginTop: 12,
                  border: '1px solid #ffccc7',
                }}>
                  <div style={{ fontWeight: 600, marginBottom: 8, color: '#ff4d4f' }}>
                    <ExclamationCircleOutlined style={{ marginRight: 4 }} />
                    错误详情：
                  </div>
                  {result.errors.map((err, i) => (
                    <div key={i} style={{ color: '#cf1322', fontSize: 12, padding: '2px 0' }}>
                      {i + 1}. {err}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ),
          width: 520,
        });
      } else {
        message.success(`导入成功，共导入 ${result.success_count} 条记录`);
      }
      fetchData();
    } catch {
      message.error('导入失败，请检查文件格式是否正确');
    } finally {
      setImporting(false);
      // 重置 input 以允许重复选择同一文件
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    }
  };

  // 刷新
  const handleRefresh = () => {
    setPage(1);
    fetchData();
    fetchDicts();
  };

  const columns = [
    { title: '学号', dataIndex: 'student_no', key: 'student_no', width: 120, ellipsis: true },
    { title: '姓名', dataIndex: 'real_name', key: 'real_name', width: 100 },
    { title: '性别', dataIndex: 'gender', key: 'gender', width: 60 },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name', width: 100 },
    { title: '班级', dataIndex: 'class_name', key: 'class_name', width: 100 },
    { title: '登录账号', dataIndex: 'username', key: 'username', width: 120, ellipsis: true },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'red'} style={{ borderRadius: 4 }}>
          {v ? '启用' : '停用'}
        </Tag>
      ),
    },
    {
      title: '操作', key: 'action', width: 180, fixed: 'right' as const,
      render: (_: unknown, r: UserInfo) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
              编辑
            </Button>
          </Tooltip>
          <Popconfirm
            title="确定删除该学生？"
            description="删除后不可恢复"
            onConfirm={() => handleDelete(r.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="link" danger size="small" icon={<DeleteOutlined />}>
                删除
              </Button>
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 页面标题 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 20, paddingBottom: 16,
        borderBottom: '1px solid #f0f0f0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 4, height: 20, borderRadius: 2,
            background: 'linear-gradient(180deg, #1677ff, #4096ff)',
          }} />
          <Title level={5} style={{ margin: 0, fontWeight: 600, color: '#262626' }}>
            学生管理
          </Title>
          <Tag style={{ borderRadius: 4, marginLeft: 4 }} color="processing">
            共 {total} 人
          </Tag>
        </div>
        <Space>
          <Button onClick={handleRefresh} icon={<ReloadOutlined />}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 搜索过滤 + 操作按钮 */}
      <Card
        style={{ marginBottom: 16, borderRadius: 10 }}
        bodyStyle={{ padding: '16px 20px' }}
      >
        <Row justify="space-between" align="middle" wrap gutter={[16, 12]}>
          <Col>
            <Space size="middle" wrap>
              <Select
                placeholder="选择年级"
                allowClear
                style={{ width: 130 }}
                value={filters.grade_id}
                onChange={(v) => {
                  setFilters((f) => ({ ...f, grade_id: v }));
                  setPage(1);
                }}
                options={grades.map((g) => ({ value: g.value, label: g.label }))}
              />
              <Select
                placeholder="选择班级"
                allowClear
                style={{ width: 150 }}
                value={filters.class_id}
                onChange={(v) => {
                  setFilters((f) => ({ ...f, class_id: v }));
                  setPage(1);
                }}
                options={classes.map((c) => ({ value: c.id, label: c.name }))}
              />
              <Input.Search
                placeholder="搜索姓名 / 学号 / 账号"
                allowClear
                style={{ width: 220 }}
                value={filters.keyword}
                onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value }))}
                onSearch={() => {
                  setPage(1);
                  fetchData();
                }}
                prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
              />
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Button
                icon={<DownloadOutlined />}
                onClick={handleDownloadTemplate}
              >
                下载导入模板
              </Button>
              <Button
                icon={<UploadOutlined />}
                onClick={handleImportClick}
                loading={importing}
                style={{
                  borderColor: '#1677ff',
                  color: '#1677ff',
                }}
              >
                批量导入
              </Button>
              {/* 隐藏的文件选择器 */}
              <input
                ref={inputRef}
                type="file"
                accept=".xlsx,.xls"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={openCreate}
              >
                新增学生
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card style={{ borderRadius: 10 }} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          dataSource={data}
          columns={columns}
          loading={loading}
          scroll={{ x: 900 }}
          size="middle"
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: (p) => setPage(p),
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条记录`,
            style: { padding: '12px 20px' },
          }}
        />
      </Card>

      {/* 新增 / 编辑弹窗 */}
      <Modal
        title={editingStudent ? '编辑学生信息' : '新增学生'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
        width={560}
        style={{ maxWidth: '95vw' }}
        okText={editingStudent ? '保存修改' : '确认新增'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="student_no" label="学号" rules={[{ required: true, message: '请输入学号' }]}>
                <Input placeholder="请输入学号" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="real_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
                <Input placeholder="请输入姓名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="username" label="登录账号" rules={[{ required: true, message: '请输入登录账号' }]}>
                <Input
                  disabled={!!editingStudent}
                  placeholder={editingStudent ? '' : '默认同化学号'}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              {!editingStudent && (
                <Form.Item name="password" label="初始密码" tooltip="留空则默认 123456">
                  <Input placeholder="默认 123456" />
                </Form.Item>
              )}
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="gender" label="性别">
                <Select
                  options={[
                    { value: '男', label: '男' },
                    { value: '女', label: '女' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="grade_id" label="年级">
                <Select
                  placeholder="选择年级"
                  options={grades.map((g) => ({ value: g.value, label: g.label }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="class_id" label="班级">
                <Select
                  placeholder="选择班级"
                  options={classes.map((c) => ({ value: c.id, label: c.name }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="phone" label="手机号">
                <Input placeholder="请输入手机号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="status" label="状态">
                <Select
                  options={[
                    { value: true, label: '启用' },
                    { value: false, label: '停用' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
