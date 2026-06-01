import { useState, useEffect } from 'react';
import { Drawer, Descriptions, Tag, Table, Card, Empty, Spin, Space, Progress, Row, Col, Statistic, Typography, Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import client from '../../api/client';
import { RISK_LABELS, RISK_COLORS, DIMENSION_LABELS, VALIDITY_LABELS, QUALITY_LABELS, RISK_TAG_LABELS } from '../../utils/constants';
import { translateRiskType } from '../../utils/maskIdCard';

interface Props {
  answerSheetId?: number;
  alertId?: number;
  platformMode?: boolean;
  open: boolean;
  onClose: () => void;
}

export default function AnswerDetail({ answerSheetId, alertId, platformMode = false, open, onClose }: Props) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [drawerWidth, setDrawerWidth] = useState(960);

  useEffect(() => {
    const w = Math.min(window.innerWidth - 40, 1200);
    setDrawerWidth(w);
    const handleResize = () => setDrawerWidth(Math.min(window.innerWidth - 40, 1200));
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setDetail(null);
    const fetchDetail = async () => {
      try {
        let url: string;
        if (alertId) {
          url = platformMode ? `/platform/risks/${alertId}/answers` : `/risks/${alertId}/answers`;
        } else if (answerSheetId) {
          url = platformMode ? `/platform/answer-sheets/${answerSheetId}/detail` : `/risks/sheets/${answerSheetId}/detail`;
        } else return;
        const r = await client.get(url);
        if (!cancelled) setDetail(r.data.data);
      } catch { if (!cancelled) setDetail(null); }
      finally { if (!cancelled) setLoading(false); }
    };
    fetchDetail();
    return () => { cancelled = true; };
  }, [open, answerSheetId, alertId, platformMode]);

  const formatDuration = (seconds: number) => {
    if (!seconds) return '-';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}分${s}秒` : `${s}秒`;
  };

  const questionColumns = [
    {
      title: '序号', width: 50, render: (_: any, __: any, idx: number) => idx + 1,
    },
    {
      title: '维度', dataIndex: 'dimension_label', width: 90,
      render: (v: string) => v || '-',
    },
    {
      title: '题目', dataIndex: 'question_title', width: 240, ellipsis: true,
    },
    {
      title: '选项', dataIndex: 'options', width: 220,
      render: (options: any[], record: any) => {
        const selectedIds = record.selected_option_ids || [];
        return (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {(options || []).map((opt: any) => {
              const isSelected = selectedIds.includes(opt.option_id ?? opt.id);
              return (
                <Tag key={opt.option_id ?? opt.id} color={isSelected ? 'blue' : undefined}
                  style={isSelected ? { fontWeight: 600 } : undefined}>
                  {opt.content}{isSelected ? ' ✓' : ''}
                </Tag>
              );
            })}
          </div>
        );
      },
    },
    {
      title: '得分', dataIndex: 'score', width: 60, align: 'center' as const,
      render: (v: number, r: any) => {
        if (r.is_attention_check) return <Tag color="purple">检</Tag>;
        return <span style={{ fontWeight: v > 0 ? 600 : 400 }}>{v}</span>;
      },
    },
    {
      title: '耗时', dataIndex: 'duration_seconds', width: 70, align: 'center' as const,
      render: (v: number) => formatDuration(v),
    },
    {
      title: '风险', dataIndex: 'risk_tag', width: 120,
      render: (v: string) => v ? <Tag color="orange">{RISK_TAG_LABELS[v] || '未知'}</Tag> : '-',
    },
  ];

  return (
    <Drawer title="答题详情" open={open} onClose={onClose} width={drawerWidth} destroyOnClose>
      {loading ? <Spin /> : detail ? (
        <div>
          <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="学生">{detail.student_name}</Descriptions.Item>
            <Descriptions.Item label="学号">{detail.student_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="问卷">{detail.questionnaire_title}</Descriptions.Item>
            <Descriptions.Item label="任务">{detail.task_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="提交时间">{detail.submitted_at ? new Date(detail.submitted_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            <Descriptions.Item label="总用时">{formatDuration(detail.total_duration_seconds)}</Descriptions.Item>
          </Descriptions>

          {detail.scoring && (
            <Card title="评分概览" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16} style={{ marginBottom: 12 }}>
                <Col span={6}><Statistic title="总分" value={detail.scoring.total_score} /></Col>
                <Col span={6}>
                  <Statistic title="风险等级"
                    value={RISK_LABELS[detail.scoring.risk_level] || '未知'}
                    valueStyle={{ color: RISK_COLORS[detail.scoring.risk_level] }} />
                </Col>
                <Col span={6}>
                  <Statistic title="风险类型" value={translateRiskType(detail.scoring.risk_type)} />
                </Col>
                <Col span={6}>
                  <Statistic title="触发规则" value={(detail.scoring.triggered_rules || []).length} />
                </Col>
              </Row>
              {detail.scoring.risk_description && (
                <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
                  {detail.scoring.risk_description}
                </Typography.Paragraph>
              )}
              {detail.scoring.dimension_scores && Object.keys(detail.scoring.dimension_scores).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Typography.Text strong>维度得分</Typography.Text>
                  <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                    {Object.entries(detail.scoring.dimension_scores).map(([key, val]) => {
                      const score = val as number;
                      const maxScore = 100;
                      return (
                        <Col span={12} key={key}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ width: 80, fontSize: 12, textAlign: 'right' }}>{detail.answers?.find((a: any) => a.dimension === key)?.dimension_label || DIMENSION_LABELS[key] || '未知'}</span>
                            <Progress percent={Math.round(score / maxScore * 100)} size="small" style={{ flex: 1 }}
                              strokeColor={score > 70 ? '#FF4D4F' : score > 40 ? '#FA8C16' : '#1890FF'} />
                            <span style={{ fontSize: 12, width: 40 }}>{score}</span>
                          </div>
                        </Col>
                      );
                    })}
                  </Row>
                </div>
              )}
            </Card>
          )}

          {detail.quality && (
            <Card title="答卷质量" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}><Statistic title="质量评分" value={detail.quality.quality_score} /></Col>
                <Col span={8}>
                  <Statistic title="质量等级" value={QUALITY_LABELS[detail.quality.quality_level] || '未知'} />
                </Col>
                <Col span={8}>
                  <Statistic title="有效性" value={VALIDITY_LABELS[detail.quality.validity] || '未知'} />
                </Col>
              </Row>
              {detail.quality.suggest_retest && (
                <Typography.Text type="warning" style={{ display: 'block', marginTop: 8 }}>建议重新测评</Typography.Text>
              )}
            </Card>
          )}

          <Card title={`逐题详情 (${detail.answers?.length || 0} 题)`} size="small">
            <Table rowKey={(_: any, i: number | undefined) => String(i)}
              dataSource={detail.answers || []}
              columns={questionColumns}
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
              expandable={{
                rowExpandable: (r: any) => r.is_attention_check || r.is_reverse,
                expandedRowRender: (r: any) => (
                  <Space>
                    {r.is_attention_check && <Tag color="purple">注意力检测题</Tag>}
                    {r.is_reverse && <Tag color="orange">反向计分</Tag>}
                  </Space>
                ),
              }}
            />
          </Card>
        </div>
      ) : <Empty description="加载失败" />}
    </Drawer>
  );
}
