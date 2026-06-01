import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Select, Input, Typography, Space, Button, Card, Modal, Form, message, Row, Col, Statistic, Empty, Spin, Upload } from 'antd';
import { CopyOutlined, DeleteOutlined, EyeOutlined, PlusOutlined, EditOutlined, SendOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { downloadPlatformTemplate, importPlatformQuestionnaire, exportPlatformQuestionnaire, batchExportQuestionnaires } from '../../api/questionnaires';
import type { ImportError } from '../../api/questionnaires';
import { QUESTIONNAIRE_STATUS_LABELS, QUESTIONNAIRE_CATEGORY_LABELS, SOURCE_TYPE_LABELS } from '../../utils/constants';

export default function PlatformQuestionnaireManagement() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ category: '', status: '', keyword: '', source_type: '' });
  const [usageOpen, setUsageOpen] = useState(false);
  const [usage, setUsage] = useState<any>(null);
  const [pushOpen, setPushOpen] = useState(false);
  const [pushQid, setPushQid] = useState<number>();
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [selectedSchools, setSelectedSchools] = useState<number[]>([]);
  const [pushLoading, setPushLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [stats, setStats] = useState({ total: 0, builtin: 0, platform: 0, school: 0 });
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importErrors, setImportErrors] = useState<ImportError[]>([]);
  const [importSuccess, setImportSuccess] = useState<any>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<any>(null);
  const [editForm] = Form.useForm();
  const [editLoading, setEditLoading] = useState(false);

  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.category) params.category = filters.category;
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.source_type) params.source_type = filters.source_type;
      const r = await client.get('/platform/questionnaires', { params });
      const items = r.data.data?.items || [];
      setData(items);
      setTotal(r.data.data?.total || 0);
      setStats({
        total: r.data.data?.total || 0,
        builtin: items.filter((i: any) => i.is_builtin).length,
        platform: items.filter((i: any) => !i.is_builtin && !i.school_id).length,
        school: items.filter((i: any) => i.school_id).length,
      });
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const viewUsage = async (qid: number) => {
    try {
      const r = await client.get(`/platform/questionnaires/${qid}/usage`);
      setUsage(r.data.data);
      setUsageOpen(true);
    } catch { message.error('获取使用统计失败'); }
  };

  const handleCopy = async (qid: number) => {
    try {
      const r = await client.post(`/platform/questionnaires/${qid}/copy`);
      message.success(r.data.message || '复制成功');
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '复制失败');
    }
  };

  const handleDelete = async (qid: number) => {
    try {
      await client.delete(`/platform/questionnaires/${qid}`);
      message.success('删除成功');
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  const handlePush = async () => {
    if (!selectedSchools.length) { message.warning('请选择目标学校'); return; }
    setPushLoading(true);
    try {
      const r = await client.post(`/platform/questionnaires/${pushQid}/push`, { school_ids: selectedSchools });
      message.success(r.data.message || '推送成功');
      setPushOpen(false);
      setSelectedSchools([]);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '推送失败');
    } finally { setPushLoading(false); }
  };

  const handleCreate = async () => {
    setCreateOpen(false);
    message.info('问卷已创建，请在学校端编辑题目');
  };

  const handleDownloadTemplate = async () => {
    try {
      await downloadPlatformTemplate();
      message.success('模板下载成功');
    } catch { message.error('下载模板失败'); }
  };

  const handleImport = async (file: File) => {
    setImportLoading(true);
    setImportErrors([]);
    setImportSuccess(null);
    try {
      const result = await importPlatformQuestionnaire(file);
      if (result.success) {
        setImportSuccess(result);
        message.success(`导入成功：${result.title}，共 ${result.question_count} 题`);
        fetchData();
      } else {
        setImportErrors(result.errors || []);
        message.error(`导入失败，共发现 ${result.total_errors || 0} 个错误`);
      }
    } catch {
      setImportErrors([{ row: 0, field: '文件', message: '导入失败，请检查文件格式' }]);
    } finally { setImportLoading(false); }
    return false;
  };

  const handleExport = async (record: any) => {
    try {
      await exportPlatformQuestionnaire(record.id, record.title);
      message.success('导出成功');
    } catch { message.error('导出失败'); }
  };

  const handleBatchExport = async () => {
    if (!selectedRowKeys.length) { message.warning('请先选择要导出的问卷'); return; }
    try {
      await batchExportQuestionnaires(selectedRowKeys as number[]);
      message.success(`已导出 ${selectedRowKeys.length} 套问卷`);
    } catch { message.error('批量导出失败'); }
  };

  const openEdit = async (record: any) => {
    try {
      const r = await client.get(`/platform/questionnaires/${record.id}`);
      const d = r.data.data;
      setEditRecord(d);
      editForm.setFieldsValue({
        title: d.title, description: d.description, category: d.category,
        applicable_grades: d.applicable_grades, disclaimer: d.disclaimer,
      });
      setEditModalOpen(true);
    } catch { message.error('获取问卷信息失败'); }
  };

  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields();
      setEditLoading(true);
      await client.put(`/platform/questionnaires/${editRecord.id}`, values);
      message.success('更新成功');
      setEditModalOpen(false);
      setEditRecord(null);
      editForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail || '更新失败');
    } finally { setEditLoading(false); }
  };

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', width: 200, ellipsis: true,
      render: (v: string, r: any) => <a onClick={() => navigate(`/platform/questionnaires/${r.id}/edit`)}>{v}</a> },
    { title: '类别', dataIndex: 'category', key: 'category', width: 90,
      render: (v: string) => <Tag>{QUESTIONNAIRE_CATEGORY_LABELS[v] || v || '-'}</Tag> },
    { title: '来源', key: 'source', width: 100,
      render: (_: any, r: any) => {
        if (r.is_builtin) return <Tag color="blue">内置</Tag>;
        if (r.school_id) return <Tag color="green">学校</Tag>;
        return <Tag color="orange">平台</Tag>;
      },
    },
    { title: '题目数', dataIndex: 'question_count', key: 'question_count', width: 70, align: 'center' as const },
    { title: '使用次数', dataIndex: 'task_count', key: 'task_count', width: 80, align: 'center' as const },
    { title: '答卷数', dataIndex: 'answer_count', key: 'answer_count', width: 70, align: 'center' as const },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => <Tag color={v === 'published' ? 'green' : v === 'draft' ? 'default' : 'blue'}>{QUESTIONNAIRE_STATUS_LABELS[v] || v}</Tag> },
    { title: '操作', key: 'action', width: 340, render: (_: any, r: any) => (
      <Space>
        <Button size="small" type="link" icon={<EyeOutlined />} onClick={() => navigate(`/platform/questionnaires/${r.id}/edit`)}>详情</Button>
        <Button size="small" type="link" onClick={() => viewUsage(r.id)}>统计</Button>
        <Button size="small" type="link" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
        {!r.is_builtin && <Button size="small" type="link" icon={<CopyOutlined />} onClick={() => handleCopy(r.id)}>复制</Button>}
        <Button size="small" type="link" icon={<SendOutlined />} onClick={() => { setPushQid(r.id); setPushOpen(true); }}>推送</Button>
        <Button size="small" type="link" icon={<DownloadOutlined />} onClick={() => handleExport(r)}>导出</Button>
        {!r.is_builtin && (
          <Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => Modal.confirm({
            title: '确定删除？', content: r.status !== 'draft' ? `该问卷状态为「${QUESTIONNAIRE_STATUS_LABELS[r.status] || r.status}」，删除后关联的任务和答卷数据将一并清除，不可恢复！` : '删除后不可恢复',
            okType: 'danger', onOk: () => handleDelete(r.id),
          })}>删除</Button>
        )}
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>问卷管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/platform/questionnaires/new')}>新建问卷</Button>
      </div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="问卷总数" value={stats.total} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="内置问卷" value={stats.builtin} valueStyle={{ color: '#1890FF' }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="平台问卷" value={stats.platform} valueStyle={{ color: '#FA8C16' }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="学校问卷" value={stats.school} valueStyle={{ color: '#52C41A' }} /></Card></Col>
      </Row>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="类别" allowClear style={{ width: 130 }} value={filters.category || undefined}
          onChange={v => setFilters(f => ({ ...f, category: v || '' }))}
          options={Object.entries(QUESTIONNAIRE_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <Select placeholder="来源" allowClear style={{ width: 130 }} value={filters.source_type || undefined}
          onChange={v => setFilters(f => ({ ...f, source_type: v || '' }))}
          options={Object.entries(SOURCE_TYPE_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
        <Input.Search placeholder="搜索问卷标题" style={{ width: 200 }} value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
        <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>下载模板</Button>
        <Button icon={<UploadOutlined />} onClick={() => { setImportModalOpen(true); setImportErrors([]); setImportSuccess(null); }}>导入问卷</Button>
        {selectedRowKeys.length > 0 && (
          <Button icon={<DownloadOutlined />} type="primary" ghost onClick={handleBatchExport}>
            批量导出 ({selectedRowKeys.length})
          </Button>
        )}
      </Space>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 套问卷` }} />

      <Modal title="使用统计" open={usageOpen} onCancel={() => setUsageOpen(false)} footer={null} width={500} destroyOnClose>
        {usage ? (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}><Statistic title="关联任务" value={usage.task_count} /></Col>
              <Col span={8}><Statistic title="答卷数" value={usage.answer_count} /></Col>
              <Col span={8}><Statistic title="已提交" value={usage.submitted} /></Col>
            </Row>
            {usage.copies > 0 && <p>已推送到 {usage.copies} 所学校的副本</p>}
            {usage.schools?.length ? (
              <Card title="使用学校" size="small">
                {usage.schools.map((s: any) => <Tag key={s.id}>{s.name}</Tag>)}
              </Card>
            ) : <Empty description="暂无学校使用" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </div>
        ) : null}
      </Modal>

      <Modal title="推送到学校" open={pushOpen} onCancel={() => { setPushOpen(false); setSelectedSchools([]); }}
        onOk={handlePush} confirmLoading={pushLoading} destroyOnClose width={500} okText="推送" cancelText="取消">
        <p style={{ marginBottom: 12 }}>选择要推送此问卷的学校（已推送的学校不会重复推送）</p>
        <Select mode="multiple" placeholder="选择学校" style={{ width: '100%' }}
          value={selectedSchools} onChange={setSelectedSchools}
          options={schools} showSearch optionFilterProp="label" />
      </Modal>

      <Modal title="导入问卷" open={importModalOpen} onCancel={() => setImportModalOpen(false)}
        footer={null} destroyOnClose width={700}>
        {!importSuccess && (
          <>
            <Upload.Dragger accept=".xlsx,.xls" maxCount={1} showUploadList={false}
              beforeUpload={(file) => { handleImport(file); return false; }}
              disabled={importLoading}>
              <p className="ant-upload-drag-icon"><UploadOutlined style={{ fontSize: 32, color: '#1890ff' }} /></p>
              <p>点击或拖拽 Excel 文件到此处上传</p>
              <p style={{ color: '#999', fontSize: 12 }}>仅支持 .xlsx 格式</p>
            </Upload.Dragger>
            {importLoading && <Spin style={{ display: 'block', margin: '16px auto' }} tip="正在导入..." />}
            {importErrors.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography.Text type="danger">发现 {importErrors.length} 个错误，请修正后重新导入：</Typography.Text>
                <Table rowKey={(_, i) => String(i)} dataSource={importErrors} size="small" pagination={false}
                  style={{ marginTop: 8 }}
                  columns={[
                    { title: '行号', dataIndex: 'row', width: 60, render: (v: number) => v > 0 ? `第 ${v} 行` : '-' },
                    { title: '字段', dataIndex: 'field', width: 120 },
                    { title: '错误信息', dataIndex: 'message' },
                  ]} />
              </div>
            )}
          </>
        )}
        {importSuccess && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <Typography.Title level={4} style={{ color: '#52c41a' }}>导入成功</Typography.Title>
            <p>问卷：<strong>{importSuccess.title}</strong></p>
            <p>题目数：<strong>{importSuccess.question_count}</strong></p>
            <p>状态：<Tag>{QUESTIONNAIRE_STATUS_LABELS[importSuccess.status] || '草稿'}</Tag></p>
            <Button type="primary" onClick={() => setImportModalOpen(false)} style={{ marginTop: 16 }}>完成</Button>
          </div>
        )}
      </Modal>

      <Modal title={`编辑问卷 - ${editRecord?.title || ''}`} open={editModalOpen}
        onOk={handleEdit} confirmLoading={editLoading}
        onCancel={() => { setEditModalOpen(false); setEditRecord(null); editForm.resetFields(); }}
        destroyOnClose width={600} style={{ maxWidth: '95vw' }} okText="保存" cancelText="取消">
        <Form form={editForm} layout="vertical">
          <Form.Item name="title" label="问卷标题" rules={[{ required: true, message: '请输入问卷标题' }]}>
            <Input placeholder="请输入问卷标题" />
          </Form.Item>
          <Form.Item name="description" label="问卷描述">
            <Input.TextArea rows={3} placeholder="请输入问卷描述" />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Select placeholder="选择分类"
              options={Object.entries(QUESTIONNAIRE_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="applicable_grades" label="适用年级">
            <Input placeholder="如：初一,初二,初三" />
          </Form.Item>
          <Form.Item name="disclaimer" label="免责声明">
            <Input.TextArea rows={2} placeholder="学生答题前显示的知情同意内容" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
