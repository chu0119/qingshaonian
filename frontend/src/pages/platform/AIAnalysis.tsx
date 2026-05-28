import { useState, useEffect, useCallback } from 'react';
import { Table, Typography, Tag, Button, Spin, Empty, Space, Card, message } from 'antd';
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function PlatformAIAnalysis() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState('');

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const r = await client.get('/platform/ai-logs', { params: { page, page_size: 20 } });
      setLogs(r.data.data.items); setTotal(r.data.data.total);
    } catch { /* AI未配置时忽略 */ } finally { setLoading(false); }
  }, [page]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const runRegionalAnalysis = async () => {
    setAnalyzing(true); setAnalysisResult('');
    try {
      const r = await client.post('/platform/ai-analysis/regional');
      setAnalysisResult(r.data.data?.analysis || '暂无分析结果');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '分析失败');
    } finally { setAnalyzing(false); }
  };

  const statusColors: Record<string, string> = { success: 'green', failure: 'red', not_configured: 'default' };

  return (
    <div>
      <Typography.Title level={4}>AI 研判分析</Typography.Title>

      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<RobotOutlined />} loading={analyzing} onClick={runRegionalAnalysis}>
            区域综合分析
          </Button>
          <Typography.Text type="secondary">
            基于全平台数据生成区域风险态势研判报告
          </Typography.Text>
        </Space>
        {analyzing && <div style={{ textAlign: 'center', padding: 40 }}><Spin /><div style={{ marginTop: 12, color: '#888' }}>AI 正在分析...</div></div>}
        {analysisResult && (
          <div style={{ marginTop: 16, padding: 16, background: '#fafafa', borderRadius: 8, whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8, maxHeight: 400, overflow: 'auto' }}>
            {analysisResult}
            <div style={{ marginTop: 12, color: '#999', fontSize: 12 }}>
              {/* 免责声明 */}本分析仅作为学校教育管理、风险防范和学生关怀参考，不作为医学诊断依据。
            </div>
          </div>
        )}
      </Card>

      <Card title="AI 分析调用记录">
        <Table rowKey="id" dataSource={logs} columns={[
          { title: '时间', dataIndex: 'created_at', width: 160, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
          { title: '分析类型', dataIndex: 'analysis_type', width: 120 },
          { title: '模型', dataIndex: 'model_name', width: 120, render: (v: string) => v || '-' },
          { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
          { title: '耗时(ms)', dataIndex: 'duration_ms', width: 90 },
          { title: '操作人', dataIndex: 'user_role', width: 100 },
          { title: '错误信息', dataIndex: 'error_message', ellipsis: true, width: 200 },
        ]} loading={loading} scroll={{ x: 'max-content' }}
          pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
          locale={{ emptyText: <Empty description="暂无 AI 分析记录" /> }} />
      </Card>
    </div>
  );
}
