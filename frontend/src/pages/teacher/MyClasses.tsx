import { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Statistic, List, Tag, Progress, message, Empty, Spin, Collapse } from 'antd';
import { BankOutlined, TeamOutlined, UserOutlined, ExpandOutlined, FileTextOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function MyClasses() {
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedClass, setExpandedClass] = useState<number | null>(null);
  const [studentList, setStudentList] = useState<any[]>([]);
  const [studentLoading, setStudentLoading] = useState(false);

  useEffect(() => {
    const fetchClasses = async () => {
      setLoading(true);
      try {
        const r = await client.get('/classes/my');
        setClasses(r.data.data || []);
      } catch (err: any) {
        message.error(err._friendlyMessage || '获取班级列表失败');
      } finally {
        setLoading(false);
      }
    };
    fetchClasses();
  }, []);

  const handleExpandClass = async (classId: number) => {
    if (expandedClass === classId) {
      setExpandedClass(null);
      setStudentList([]);
      return;
    }
    setExpandedClass(classId);
    setStudentLoading(true);
    setStudentList([]);
    try {
      const r = await client.get('/users/students', { params: { class_id: classId, page: 1, page_size: 200 } });
      setStudentList(r.data.data?.items || r.data.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取班级学生完成情况失败');
    } finally {
      setStudentLoading(false);
    }
  };

  const getCompletionPercent = (completed: number, total: number) => {
    if (!total || total === 0) return 0;
    return Math.round((completed / total) * 100);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div>
      <Typography.Title level={4}>我的班级</Typography.Title>

      {classes.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Empty description="暂未分配班级" />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {classes.map((c: any) => (
            <Col xs={24} sm={12} md={8} key={c.id}>
              <Card
                hoverable
                onClick={() => handleExpandClass(c.id)}
                style={{
                  cursor: 'pointer',
                  borderColor: expandedClass === c.id ? '#4A90D9' : undefined,
                  boxShadow: expandedClass === c.id ? '0 0 0 2px rgba(74,144,217,0.2)' : undefined,
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <BankOutlined style={{ fontSize: 36, color: '#4A90D9', marginBottom: 8 }} />
                  <div style={{ fontWeight: 500, fontSize: 16 }}>
                    {c.grade_name} {c.name}
                    <ExpandOutlined style={{ marginLeft: 8, fontSize: 14, color: '#bbb' }} />
                  </div>
                  <div style={{ color: '#888', marginTop: 8 }}>
                    <TeamOutlined style={{ marginRight: 4 }} />
                    学生人数: {c.student_count || 0}
                  </div>
                  <Tag color={c.status ? 'green' : 'red'} style={{ marginTop: 8 }}>
                    {c.status ? '正常' : '停用'}
                  </Tag>
                </div>

                {/* 展开的学生完成情况区域 */}
                {expandedClass === c.id && (
                  <div
                    style={{ marginTop: 16, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Typography.Text strong style={{ fontSize: 14 }}>
                      <FileTextOutlined style={{ marginRight: 4 }} />
                      学生测评完成情况
                    </Typography.Text>

                    {studentLoading ? (
                      <div style={{ textAlign: 'center', padding: 20 }}><Spin size="small" /></div>
                    ) : studentList.length === 0 ? (
                      <Empty description="暂无学生完成数据" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 12 }} />
                    ) : (
                      <List
                        size="small"
                        style={{ marginTop: 8 }}
                        dataSource={studentList}
                        renderItem={(item: any) => {
                          const pct = getCompletionPercent(item.completed_count, item.total_count);
                          return (
                            <List.Item>
                              <List.Item.Meta
                                avatar={<UserOutlined style={{ fontSize: 20, color: '#4A90D9' }} />}
                                title={item.student_name || item.real_name || `学生 ${item.student_id}`}
                                description={
                                  item.task_name
                                    ? `${item.task_name} - ${item.questionnaire_title || ''}`
                                    : `学号: ${item.student_no || '-'}`
                                }
                              />
                              <div style={{ textAlign: 'right', minWidth: 100 }}>
                                {item.completed_count !== undefined ? (
                                  <>
                                    <Progress
                                      percent={pct}
                                      size="small"
                                      status={pct === 100 ? 'success' : 'active'}
                                      style={{ width: 80 }}
                                    />
                                    <div style={{ fontSize: 12, color: '#888' }}>
                                      {item.completed_count}/{item.total_count}
                                    </div>
                                  </>
                                ) : (
                                  <Tag color={item.completed ? 'green' : 'blue'}>
                                    {item.completed ? '已完成' : '未完成'}
                                  </Tag>
                                )}
                              </div>
                            </List.Item>
                          );
                        }}
                      />
                    )}
                  </div>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}
