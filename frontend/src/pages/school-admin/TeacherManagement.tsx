import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, Select, message, Popconfirm, Transfer } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons';
import { getTeachers, createTeacher, updateTeacher, deleteTeacher, getDictTeacherTypes, assignTeacherClasses, getTeacherAssignedClasses, type UserInfo } from '../../api/users';
import { getClasses, type ClassInfo } from '../../api/classes';

export default function TeacherManagement() {
  const [data, setData] = useState<UserInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ keyword: '', teacher_type: '' });
  const [modalOpen, setModalOpen] = useState(false);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<UserInfo | null>(null);
  const [assignTeacherId, setAssignTeacherId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [teacherTypes, setTeacherTypes] = useState<{ value: string; label: string }[]>([]);
  const [allClasses, setAllClasses] = useState<ClassInfo[]>([]);
  const [assignedKeys, setAssignedKeys] = useState<string[]>([]);
  const [assignLoading, setAssignLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.teacher_type) params.teacher_type = filters.teacher_type;
      const res = await getTeachers(params);
      setData(res.items);
      setTotal(res.total);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { getDictTeacherTypes().then(setTeacherTypes); getClasses({ page: 1, page_size: 100 }).then(r => setAllClasses(r.items)); }, []);

  const openCreate = () => {
    setEditingTeacher(null);
    form.resetFields();
    form.setFieldsValue({ status: true, role: 'teacher' });
    setModalOpen(true);
  };
  const openEdit = (record: UserInfo) => {
    setEditingTeacher(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };
  const handleDelete = async (id: number) => {
    try { await deleteTeacher(id); message.success('删除成功'); fetchData(); }
    catch { message.error('删除失败，请重试'); }
  };
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingTeacher) { await updateTeacher(editingTeacher.id, values); message.success('更新成功'); }
      else { await createTeacher(values); message.success('创建成功'); }
      setModalOpen(false); fetchData();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('操作失败，请重试');
    }
  };

  const openAssign = async (record: UserInfo) => {
    setAssignTeacherId(record.id);
    setAssignedKeys([]);
    setAssignModalOpen(true);
    setAssignLoading(true);
    try {
      const classIds = await getTeacherAssignedClasses(record.id);
      setAssignedKeys(classIds.map(String));
    } catch {
      message.error('获取已分配班级失败');
    } finally {
      setAssignLoading(false);
    }
  };
  const handleAssign = async () => {
    if (assignTeacherId) {
      await assignTeacherClasses(assignTeacherId, assignedKeys.map(Number));
      message.success('班级分配成功');
      setAssignModalOpen(false);
    }
  };

  const columns = [
    { title: '工号', dataIndex: 'username', key: 'username' },
    { title: '姓名', dataIndex: 'real_name', key: 'real_name' },
    { title: '手机号', dataIndex: 'phone', key: 'phone', render: (v: string) => v || '-' },
    { title: '教师类型', dataIndex: 'teacher_type', key: 'teacher_type', render: (v: string) => {
      const m: Record<string, string> = { head_teacher: '班主任', counselor: '心理老师', grade_director: '年级主任', moral_edu: '德育老师', normal: '普通教师' };
      return m[v] || v || '-';
    }},
    { title: '角色', dataIndex: 'role', key: 'role', render: (v: string) => v === 'counselor' ? <Tag color="purple">心理老师</Tag> : <Tag color="blue">教师</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '停用'}</Tag> },
    { title: '操作', key: 'action', width: 180, render: (_: unknown, r: UserInfo) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Button size="small" icon={<TeamOutlined />} onClick={() => openAssign(r)}>分配班级</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}><Button size="small" danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>
        </Space>
    )},
  ];

  const roleOptions = [
    { value: 'teacher', label: '教师' },
    { value: 'counselor', label: '心理老师' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Space>
          <Select placeholder="教师类型" allowClear style={{ width: 120 }} value={filters.teacher_type || undefined} onChange={v => setFilters(f => ({ ...f, teacher_type: v || '' }))} options={teacherTypes.map(t => ({ value: t.value, label: t.label }))} />
          <Input.Search placeholder="搜索姓名/工号" style={{ width: 180 }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增教师</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />

      <Modal title={editingTeacher ? '编辑教师' : '新增教师'} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} destroyOnHidden width={520} style={{ maxWidth: '95vw' }}>
        <Form form={form} layout="vertical">
          <Form.Item name="real_name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="username" label="工号" rules={[{ required: true }]}><Input disabled={!!editingTeacher} /></Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}><Select options={roleOptions} /></Form.Item>
          <Form.Item name="teacher_type" label="教师类型"><Select options={teacherTypes.map(t => ({ value: t.value, label: t.label }))} /></Form.Item>
          {!editingTeacher && <Form.Item name="password" label="初始密码"><Input placeholder="默认 123456" /></Form.Item>}
          <Form.Item name="phone" label="手机号"><Input /></Form.Item>
          <Form.Item name="status" label="状态"><Select options={[{ value: true, label: '启用' }, { value: false, label: '停用' }]} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="分配班级" open={assignModalOpen} onOk={handleAssign} okButtonProps={{ disabled: assignLoading }} confirmLoading={assignLoading} onCancel={() => setAssignModalOpen(false)} width={520} style={{ maxWidth: '95vw' }}>
        <Transfer
          dataSource={allClasses.map(c => ({ key: String(c.id), title: `${c.grade_name} ${c.name}` }))}
          targetKeys={assignedKeys}
          onChange={(targetKeys) => setAssignedKeys(targetKeys.map(String))}
          render={item => item.title}
          titles={['可选班级', '已分配班级']}
          listStyle={{ width: 220, height: 300 }}
        />
      </Modal>
    </div>
  );
}
