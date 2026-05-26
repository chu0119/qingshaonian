import { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Progress, Tag, Typography, message, Modal, Descriptions, Empty, Spin } from 'antd';
import { BankOutlined, TeamOutlined, FileTextOutlined, AlertOutlined, SafetyOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function ClassReport() {
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedClass, setSelectedClass] = useState<any>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const fetchClasses = async () => {
      setLoading(true);
      try {
        const r = await client.get('/classes/my');
        setClasses(r.data.data || []);
      } catch (err: any) {
        message.error(err?.response?.data?.message || '获取班级列表失败');
      } finally {
        setLoading(false);
      }
    };
    fetchClasses();
  }, []);

  const handleViewReport = async (cls: any) => {
    setSelectedClass(cls);
    setModalOpen(true);
    setReportLoading(true);
    setReportData(null);
    try {
      const r = await client.get('/reports/school-overview', { params: { class_id: cls.id } });
      setReportData(r.data.data);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取班级报告失败');
      setModalOpen(false);
    } finally {
      setReportLoading(false);
    }
  };

  const getCompletionPercent = (completed: number, total: number) => {
    if (!total || total === 0) return 0;
    return Math.round((completed / total) * 100);
  };

  const getRiskTagColor = (level: string) => {
    switch (level) {
      case 'high': return 'red';
      case 'medium': return 'orange';
      case 'low': return 'green';
      default: return 'default';
    }
  };

  const getRiskTagText = (level: string) => {
    switch (level) {
      case 'high': return '高风险';
      case 'medium': return '中风险';
      case 'low': return '低风险';
      default: return '无风险';
    }
  };

  return (
    <div>
      <Typography.Title level={4}>班级报告</Typography.Title>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" tip="加载中..." /></div>
      ) : classes.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          <Empty description="暂未分配班级" />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {classes.map((cls: any) => {
            const completionPercent = getCompletionPercent(cls.completed_count || 0, cls.student_count || 0);
            return (
              <Col xs={24} sm={12} md={8} lg={6} key={cls.id}>
                <Card
                  hoverable
                  onClick={() => handleViewReport(cls)}
                  style={{ cursor: 'pointer' }}
                >
                  <div style={{ textAlign: 'center' }}>
                    <BankOutlined style={{ fontSize: 40, color: '#4A90D9', marginBottom: 12 }} />
                    <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>
                      {cls.grade_name} {cls.name}
                    </div>
                    <div style={{ color: '#888', fontSize: 13, marginBottom: 12 }}>
                      <TeamOutlined style={{ marginRight: 4 }} />
                      学生数: {cls.student_count || 0}
                    </div>
                    <Progress
                      percent={completionPercent}
                      size="small"
                      status={completionPercent === 100 ? 'success' : 'active'}
                      format={() => `${completionPercent}%`}
                    />
                    <div style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
                      完成率: {cls.completed_count || 0}/{cls.student_count || 0}
                    </div>
                    {cls.risk_count > 0 && (
                      <Tag color="red" style={{ marginTop: 8 }}>
                        <AlertOutlined /> {cls.risk_count} 条风险提示
                      </Tag>
                    )}
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {/* 班级详细报告弹窗 */}
      <Modal
        title={`${selectedClass?.grade_name || ''} ${selectedClass?.name || ''} - 详细报告`}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        width={700}
        destroyOnClose
      >
        {reportLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>
        ) : reportData ? (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={12} sm={6}>
                <Card size="small" style={{ textAlign: 'center' }}>
                  <Statistic
                    title="学生数"
                    value={reportData.student_count || 0}
                    prefix={<TeamOutlined />}
                    valueStyle={{ color: '#4A90D9' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" style={{ textAlign: 'center' }}>
                  <Statistic
                    title="完成测评数"
                    value={reportData.completed_count || 0}
                    prefix={<FileTextOutlined />}
                    valueStyle={{ color: '#67C23A' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" style={{ textAlign: 'center' }}>
                  <Statistic
                    title="完成率"
                    value={getCompletionPercent(reportData.completed_count, reportData.student_count)}
                    suffix="%"
                    valueStyle={{ color: '#E6A23C' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card size="small" style={{ textAlign: 'center' }}>
                  <Statistic
                    title="风险提示数"
                    value={reportData.risk_count || 0}
                    prefix={<AlertOutlined />}
                    valueStyle={{ color: reportData.risk_count > 0 ? '#FF4D4F' : '#52c41a' }}
                  />
                </Card>
              </Col>
            </Row>

            <Descriptions bordered column={1} size="small" title="质量概况">
              <Descriptions.Item label="整体风险等级">
                <Tag color={getRiskTagColor(reportData.risk_level)}>
                  {getRiskTagText(reportData.risk_level)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="高风险提示数">
                {reportData.high_risk_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="中风险提示数">
                {reportData.medium_risk_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="低风险提示数">
                {reportData.low_risk_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="测评进度">
                <Progress
                  percent={getCompletionPercent(reportData.completed_count, reportData.student_count)}
                  size="small"
                  status={getCompletionPercent(reportData.completed_count, reportData.student_count) === 100 ? 'success' : 'active'}
                />
              </Descriptions.Item>
              {reportData.quality_summary && (
                <Descriptions.Item label="质量摘要">
                  {reportData.quality_summary}
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        ) : (
          <Empty description="暂无报告数据" />
        )}
      </Modal>
    </div>
  );
}
