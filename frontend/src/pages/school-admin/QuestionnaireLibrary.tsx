import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Button, Space, Tag, message, Popconfirm, Input, Select, Upload, Modal, Typography, Spin } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined, EyeOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { getQuestionnaires, deleteQuestionnaire, copyQuestionnaire, updateQuestionnaire, downloadQuestionnaireTemplate, importQuestionnaire, exportQuestionnaire, type QuestionnaireInfo, type ImportError } from '../../api/questionnaires';
import { QUESTIONNAIRE_CATEGORY_LABELS, SOURCE_TYPE_LABELS, QUESTIONNAIRE_STATUS_LABELS } from '../../utils/constants';
export default function QuestionnaireLibrary() {
  const navigate = useNavigate();
  const [data, setData] = useState<QuestionnaireInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ category: '', status: '', keyword: '' });
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importErrors, setImportErrors] = useState<ImportError[]>([]);
  const [importSuccess, setImportSuccess] = useState<any>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (filters.category) params.category = filters.category;
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      const res = await getQuestionnaires(params);
      setData(res?.items || []);
      setTotal(res?.total || 0);
    } finally { setLoading(false); }
  }, [page, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDelete = async (id: number) => { await deleteQuestionnaire(id); message.success('删除成功'); fetchData(); };
  const handleCopy = async (id: number) => { await copyQuestionnaire(id); message.success('复制成功'); fetchData(); };
  const handleToggleStatus = async (record: QuestionnaireInfo) => {
    const newStatus = record.status === 'active' ? 'inactive' : 'active';
    await updateQuestionnaire(record.id, { status: newStatus });
    message.success(newStatus === 'active' ? '已启用' : '已停用');
    fetchData();
  };

  const handleDownloadTemplate = async () => {
    try { await downloadQuestionnaireTemplate(); message.success('模板下载成功'); }
    catch { message.error('下载模板失败'); }
  };

  const handleImport = async (file: File) => {
    setImportLoading(true); setImportErrors([]); setImportSuccess(null);
    try {
      const result = await importQuestionnaire(file);
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

  const handleExport = async (record: QuestionnaireInfo) => {
    try { await exportQuestionnaire(record.id, record.title); message.success('导出成功'); }
    catch { message.error('导出失败'); }
  };

  const columns = [
    { title: '问卷标题', dataIndex: 'title', key: 'title', width: 260, render: (v: string, r: QuestionnaireInfo) => <a onClick={() => navigate(`/school-admin/questionnaires/${r.id}/edit`)}>{v}</a> },
    { title: '分类', dataIndex: 'category', key: 'category', render: (v: string) => <Tag>{QUESTIONNAIRE_CATEGORY_LABELS[v] || v}</Tag> },
    { title: '题目数', dataIndex: 'question_count', key: 'question_count' },
    { title: '适用年级', dataIndex: 'applicable_grades', key: 'applicable_grades', width: 180, render: (v: string) => v || '-' },
    {
      title: '维度',
      dataIndex: 'dimensions',
      key: 'dimensions',
      width: 220,
      render: (items: QuestionnaireInfo['dimensions']) =>
        items?.length ? (
          <Space size={[0, 4]} wrap>
            {items.slice(0, 3).map(item => <Tag key={item.code}>{item.title}</Tag>)}
            {items.length > 3 ? <Tag>+{items.length - 3}</Tag> : null}
          </Space>
        ) : '-',
    },
    {
      title: '类型',
      key: 'source_type',
      render: (_: unknown, r: QuestionnaireInfo) => (
        <Space size={4} wrap>
          {r.is_builtin ? <Tag color="blue">内置问卷</Tag> : <Tag>自建问卷</Tag>}
          <Tag>{SOURCE_TYPE_LABELS[r.source_type] || r.source_type}</Tag>
          <Tag>V{r.version}</Tag>
        </Space>
      ),
    },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const m: Record<string, { color: string; label: string }> = { draft: { color: 'default', label: QUESTIONNAIRE_STATUS_LABELS.draft }, active: { color: 'green', label: QUESTIONNAIRE_STATUS_LABELS.active }, inactive: { color: 'red', label: QUESTIONNAIRE_STATUS_LABELS.inactive } };
      return <Tag color={m[v]?.color}>{m[v]?.label || v}</Tag>;
    }},
    { title: '操作', key: 'action', width: 340, render: (_: unknown, r: QuestionnaireInfo) => (
        <Space>
          <Button size="small" icon={r.is_builtin ? <EyeOutlined /> : <EditOutlined />} onClick={() => navigate(`/school-admin/questionnaires/${r.id}/edit`)}>
            {r.is_builtin ? '预览' : '编辑'}
          </Button>
          <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(r.id)}>复制</Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={() => handleExport(r)}>导出</Button>
          {!r.is_builtin && <Button size="small" onClick={() => handleToggleStatus(r)}>{r.status === 'active' ? '停用' : '启用'}</Button>}
          {!r.is_builtin && r.status === 'draft' && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
    )},
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Space wrap>
          <Select placeholder="分类" allowClear style={{ width: 140, maxWidth: '100%' }} value={filters.category || undefined} onChange={v => setFilters(f => ({ ...f, category: v || '' }))}
            options={Object.entries(QUESTIONNAIRE_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          <Select placeholder="状态" allowClear style={{ width: 100, maxWidth: '100%' }} value={filters.status || undefined} onChange={v => setFilters(f => ({ ...f, status: v || '' }))}
            options={[{ value: 'draft', label: '草稿' }, { value: 'active', label: '启用' }, { value: 'inactive', label: '停用' }]} />
          <Input.Search placeholder="搜索" style={{ width: 180, maxWidth: '100%' }} value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} onSearch={fetchData} />
          <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>下载模板</Button>
          <Button icon={<UploadOutlined />} onClick={() => { setImportModalOpen(true); setImportErrors([]); setImportSuccess(null); }}>导入问卷</Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/school-admin/questionnaires/new')}>新建问卷</Button>
      </div>
      <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: t => `共 ${t} 条` }} />

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
    </div>
  );
}
