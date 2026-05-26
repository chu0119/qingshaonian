import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, Select, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getClasses, createClass, updateClass, deleteClass, type ClassInfo } from '../../api/classes';
import { getDictGrades } from '../../api/users';

export default function ClassManagement() {
  const [data, setData] = useState<ClassInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [gradeId, setGradeId] = useState<number | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingClass, setEditingClass] = useState<ClassInfo | null>(null);
  const [form] = Form.useForm();
  const [grades, setGrades] = useState<{ value: number; label: string }[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (gradeId) params.grade_id = gradeId;
      const res = await getClasses(params);
      setData(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }, [page, gradeId]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { getDictGrades().then(setGrades); }, []);

  const openCreate = () => {
    setEditingClass(null);
    form.resetFields();
    form.setFieldsValue({ status: true });
    setModalOpen(true);
  };

  const openEdit = (record: ClassInfo) => {
    setEditingClass(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try { await deleteClass(id); message.success('删除成功'); fetchData(); }
    catch { message.error('删除失败，请重试'); }
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editingClass) { await updateClass(editingClass.id, values); message.success('更新成功'); }
      else { await createClass(values); message.success('创建成功'); }
      setModalOpen(false); fetchData();
    } catch { message.error('操作失败，请重试'); }
  };

  const columns = [
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name' },
    { title: '班级名称', dataIndex: 'name', key: 'name' },
    { title: '班主任', dataIndex: 'head_teacher_name', key: 'head_teacher_name', render: (v: string) => v || '-' },
    { title: '心理老师', dataIndex: 'counselor_name', key: 'counselor_name', render: (v: string) => v || '-' },
    { title: '学生人数', dataIndex: 'student_count', key: 'student_count' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '停用'}</Tag> },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: unknown, record: ClassInfo) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除该班级？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Space>
          <Select placeholder="按年级筛选" allowClear style={{ width: 120 }} value={gradeId} onChange={setGradeId} options={grades.map(g => ({ value: g.value, label: g.label }))} />
          <Button onClick={fetchData}>查询</Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增班级</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }} />
      <Modal title={editingClass ? '编辑班级' : '新增班级'} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} destroyOnHidden>
        <Form form={form} layout="vertical">
          <Form.Item name="grade_id" label="年级" rules={[{ required: true }]}>
            <Select options={grades.map(g => ({ value: g.value, label: g.label }))} />
          </Form.Item>
          <Form.Item name="name" label="班级名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="head_teacher_id" label="班主任ID"><Input placeholder="暂用手动输入" /></Form.Item>
          <Form.Item name="counselor_id" label="心理老师ID"><Input placeholder="暂用手动输入" /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ value: true, label: '启用' }, { value: false, label: '停用' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
