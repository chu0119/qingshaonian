import { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Typography, message, Button, Space } from 'antd';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

const riskColors: Record<string, string> = { low: 'blue', medium: 'orange', high: 'red', urgent: '#CF1322' };
const riskLabels: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险', urgent: '紧急风险' };
const statusLabels: Record<string, string> = { pending: '待处理', viewed: '已查看', in_progress: '处理中', processing: '处理中', follow_up: '持续跟进', ongoing: '持续跟进', completed: '已完成', closed: '已关闭' };

export default function RiskStudents() {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const r = await client.get('/risks', { params: { page, page_size: 20 } });
      setData(r.data.data.items || []);
      setTotal(r.data.data.total || 0);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取风险提示列表失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const columns = [
    { title: '学生姓名', dataIndex: 'student_name', key: 'student_name' },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name' },
    { title: '班级', dataIndex: 'class_name', key: 'class_name' },
    { title: '风险类型', dataIndex: 'risk_type', key: 'risk_type', render: (v: string) => v || '-' },
    { title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', render: (v: string) => <Tag color={riskColors[v] || 'default'}>{riskLabels[v] || v}</Tag> },
    { title: '触发问卷', dataIndex: 'questionnaire_title', key: 'questionnaire_title', render: (v: string) => v || '-' },
    { title: '答题质量状态', dataIndex: 'quality_level', key: 'quality_level', render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{statusLabels[v] || v}</Tag> },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/teacher/interventions?student_id=${r.student_id}&risk_alert_id=${r.id}`)}>
            新增干预
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>风险提示</Typography.Title>
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
