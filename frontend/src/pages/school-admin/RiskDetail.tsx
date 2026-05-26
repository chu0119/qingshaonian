import { useState, useEffect, useCallback } from 'react';
import { Row, Col, Card, Statistic, Tag, Typography, Progress, Table, Button, Space, Descriptions, Divider, message } from 'antd';
import { TeamOutlined, UserOutlined, AlertOutlined, BankOutlined, FileTextOutlined, CheckCircleOutlined, WarningOutlined, ArrowLeftOutlined, EditOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { RobotOutlined } from '@ant-design/icons';
import client from '../../api/client';
import AiAnalysisModal from '../../components/ai/AiAnalysisModal';

const riskLabels: Record<string, { label: string; color: string }> = {
  low: { label: '低风险', color: '#1890FF' },
  medium: { label: '中风险', color: '#FA8C16' },
  high: { label: '高风险', color: '#FF4D4F' },
  urgent: { label: '紧急风险', color: '#CF1322' },
};
const qualityLabels: Record<string, string> = { normal: '正常', mild_anomaly: '轻度异常', moderate_anomaly: '中度异常', severe_anomaly: '高度异常' };
const qualityColors: Record<string, string> = { normal: '#67C23A', mild_anomaly: '#E6A23C', moderate_anomaly: '#FA8C16', severe_anomaly: '#FF4D4F' };
const validityLabels: Record<string, string> = { valid: '有效', basically_valid: '基本有效', questionable: '存疑', not_recommended: '不建议纳入核心统计' };
const statusLabels: Record<string, string> = { pending: '待处理', viewed: '已查看', processing: '处理中', ongoing: '持续跟进', completed: '已完成', closed: '已关闭' };
const dimLabels: Record<string, string> = { emotion: '情绪状态', sleep: '睡眠状态', academic_pressure: '学习压力', interpersonal: '人际关系', family_support: '家庭支持', campus_safety: '校园安全', internet_use: '网络使用', self_safety: '自我安全风险', general: '综合' };

export default function RiskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [aiOpen, setAiOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    client.get(`/risks/${id}`).then(r => {
      const d = r.data.data;
      setDetail(d);
      if (d.answer_sheet_id) {
        client.get(`/quality/${d.answer_sheet_id}`).then(r2 => setQuality(r2.data.data)).catch(() => {});
      }
    }).catch(() => {
      message.error('获取风险详情失败');
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Typography.Text>加载中...</Typography.Text>;
  if (!detail) return <Typography.Text>未找到风险记录</Typography.Text>;

  const dimScores = detail.dimension_scores || {};
  const riskInfo = riskLabels[detail.risk_level] || { label: detail.risk_level, color: '#666' };

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>返回列表</Button>
      <Typography.Title level={4}>风险详情 - {detail.student_name}</Typography.Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={16}>
          <Card title="风险信息">
            <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
              <Descriptions.Item label="学生姓名">{detail.student_name}</Descriptions.Item>
              <Descriptions.Item label="风险等级"><Tag color={riskInfo.color}>{riskInfo.label}</Tag></Descriptions.Item>
              <Descriptions.Item label="风险类型">{detail.risk_type || '暂无分类'}</Descriptions.Item>
              <Descriptions.Item label="处理状态"><Tag>{statusLabels[detail.status] || '待处理'}</Tag></Descriptions.Item>
              <Descriptions.Item label="测评总分">{detail.total_score?.toFixed(1) || '-'} 分</Descriptions.Item>
              <Descriptions.Item label="建议复测">
                <Tag color={quality?.suggest_retest ? 'red' : 'green'}>{quality?.suggest_retest ? '建议复测' : '暂不需要'}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {quality && (
            <Card title="答题质量评估" style={{ marginTop: 16 }}>
              <Row gutter={[16, 8]}>
                <Col xs={12} sm={6}><Statistic title="质量评分" value={quality.quality_score} suffix="分" valueStyle={{ color: quality.quality_score >= 80 ? '#67C23A' : quality.quality_score >= 60 ? '#E6A23C' : '#FF4D4F', fontSize: 20 }} /></Col>
                <Col xs={12} sm={6}><Statistic title="质量等级" value={qualityLabels[quality.quality_level] || quality.quality_level} valueStyle={{ color: qualityColors[quality.quality_level] || '#666', fontSize: 20 }} /></Col>
                <Col xs={12} sm={6}><Statistic title="答题时长" value={quality.total_duration_formatted || '-'} valueStyle={{ fontSize: 20 }} /></Col>
                <Col xs={12} sm={6}><Statistic title="有效性" value={validityLabels[quality.validity] || quality.validity_label || quality.validity} valueStyle={{ fontSize: 20 }} /></Col>
              </Row>
              <Divider />
              <Descriptions column={{ xs: 1, sm: 2 }} size="small">
                <Descriptions.Item label="注意力检测">{quality.attention_passed ? <Tag color="green">通过</Tag> : <Tag color="red">未通过</Tag>}</Descriptions.Item>
                <Descriptions.Item label="连续同选项最大次数">{quality.max_consecutive_same > 0 ? `${quality.max_consecutive_same} 次` : '无异常'}</Descriptions.Item>
                <Descriptions.Item label="矛盾答案组数">{quality.contradiction_count > 0 ? `${quality.contradiction_count} 组` : '无异常'}</Descriptions.Item>
                <Descriptions.Item label="规律作答">{quality.pattern_detected ? <Tag color="red">检测到</Tag> : <Tag color="green">未检测到</Tag>}</Descriptions.Item>
                <Descriptions.Item label="快速作答题数">{quality.fast_question_count > 0 ? `${quality.fast_question_count} 题` : '无异常'}</Descriptions.Item>
                <Descriptions.Item label="最高频选项占比">{quality.same_option_ratio || 0}%</Descriptions.Item>
              </Descriptions>
              {quality.deductions?.length > 0 && (
                <>
                  <Divider />
                  <Typography.Text strong style={{ color: '#FF4D4F' }}>扣分明细：</Typography.Text>
                  <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                    {quality.deductions.map((d: string, i: number) => <li key={i} style={{ color: '#FF4D4F', marginBottom: 4 }}>{d}</li>)}
                  </ul>
                </>
              )}
            </Card>
          )}
        </Col>

        <Col xs={24} md={8}>
          <Card title="维度得分">
            {Object.keys(dimScores).length === 0 ? (
              <Typography.Text type="secondary">暂无维度得分数据</Typography.Text>
            ) : (
              Object.entries(dimScores).map(([dim, score]) => (
                <div key={dim} style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 13 }}>{dimLabels[dim] || dim}</span>
                    <span style={{ fontWeight: 500 }}>{score as number} 分</span>
                  </div>
                  <Progress percent={Math.min((score as number) / 20 * 100, 100)} showInfo={false}
                    strokeColor={(score as number) > 15 ? '#FF4D4F' : (score as number) > 10 ? '#FA8C16' : '#67C23A'} size="small" />
                </div>
              ))
            )}
          </Card>

          {detail.risk_description && (
            <Card title="综合评估" style={{ marginTop: 16 }}>
              <Typography.Paragraph style={{ fontSize: 13, lineHeight: 1.8, color: '#666' }}>
                {detail.risk_description}
              </Typography.Paragraph>
            </Card>
          )}

          {detail.dimension_analysis?.length > 0 && (
            <Card title="维度分析" style={{ marginTop: 16 }}>
              {detail.dimension_analysis.map((item: any, i: number) => (
                <div key={i} style={{ marginBottom: 12, padding: '8px 12px', background: '#fafafa', borderRadius: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 500 }}>{item.label}</span>
                    <Tag color={item.level === '偏高' ? 'red' : 'orange'}>{item.level} ({item.ratio}%)</Tag>
                  </div>
                  <div style={{ fontSize: 12, color: '#888' }}>{item.suggestion}</div>
                </div>
              ))}
            </Card>
          )}

          <Card title="操作" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" block icon={<EditOutlined />}
                onClick={() => navigate('/school-admin/interventions', { state: { student_id: detail.student_id, risk_alert_id: detail.id } })}>
                新增干预记录
              </Button>
              <Button block icon={<RobotOutlined />} onClick={() => setAiOpen(true)}
                style={{ borderColor: '#00d4ff', color: '#00d4ff' }}>
                AI 智能分析
              </Button>
              <Button block onClick={() => navigate(`/school-admin/risks`)}>返回预警列表</Button>
            </Space>
          </Card>
        </Col>
      </Row>
      <AiAnalysisModal open={aiOpen} type="student_risk" data={{
        name: detail.student_name,
        risk_level: riskLabels[detail.risk_level]?.label || detail.risk_level,
        risk_type: detail.risk_type || '暂无分类',
        total_score: detail.total_score?.toFixed(1) || '-',
        dimension_scores: Object.entries(detail.dimension_scores || {}).map(([k, v]) => `${dimLabels[k] || k}: ${v}分`).join('、') || '暂无数据',
        quality_level: quality ? (qualityLabels[quality.quality_level] || quality.quality_level) : '暂无数据',
        quality_score: quality?.quality_score ?? '-',
        attention_passed: quality?.attention_passed ? '通过' : (quality ? '未通过' : '暂无数据'),
        duration: quality?.total_duration_formatted || '未知',
      }} title={`AI分析 - ${detail.student_name}`} onClose={() => setAiOpen(false)} /></div>
  );
}
