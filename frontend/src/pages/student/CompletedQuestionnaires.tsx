import { useState, useEffect } from 'react';
import { Card, List, Typography, Tag, message, Descriptions, Empty, Spin } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined, DownOutlined, RightOutlined } from '@ant-design/icons';
import client from '../../api/client';

export default function CompletedQuestionnaires() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const r = await client.get('/student/tasks/completed');
      setItems(r.data.data || []);
    } catch (err: any) {
      message.error(err?.response?.data?.message || '获取已完成问卷失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const formatDuration = (seconds: number) => {
    if (seconds === undefined || seconds === null) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) return `${mins}分${secs}秒`;
    return `${secs}秒`;
  };

  const formatDateTime = (dateStr: string) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div>
      <Typography.Title level={4}>已完成问卷</Typography.Title>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" tip="加载中..." /></div>
      ) : items.length === 0 ? (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Empty description="暂无已完成问卷" />
        </Card>
      ) : (
        <List
          dataSource={items}
          pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条记录` }}
          renderItem={(item: any) => {
            const isExpanded = expandedId === item.id || expandedId === item.task_id;
            const itemId = item.id || item.task_id;
            return (
              <Card
                size="small"
                style={{ marginBottom: 8 }}
                hoverable
                onClick={() => toggleExpand(itemId)}
              >
                {/* 标题行 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {isExpanded ? <DownOutlined style={{ color: '#4A90D9' }} /> : <RightOutlined style={{ color: '#bbb' }} />}
                    <FileTextOutlined style={{ fontSize: 18, color: '#4A90D9' }} />
                    <div>
                      <div style={{ fontWeight: 500 }}>{item.questionnaire_title || '未命名问卷'}</div>
                      <div style={{ color: '#888', fontSize: 13 }}>{item.task_name || '-'}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Tag color="green" icon={<CheckCircleOutlined />}>已完成</Tag>
                    <div style={{ color: '#888', fontSize: 12, marginTop: 2 }}>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {item.submitted_at?.split('T')[0] || '-'}
                    </div>
                  </div>
                </div>

                {/* 展开的详细信息 */}
                {isExpanded && (
                  <div
                    style={{
                      marginTop: 12,
                      borderTop: '1px solid #f0f0f0',
                      paddingTop: 12,
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
                      <Descriptions.Item label="问卷名称">
                        {item.questionnaire_title || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="所属任务">
                        {item.task_name || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="提交时间">
                        {formatDateTime(item.submitted_at)}
                      </Descriptions.Item>
                      <Descriptions.Item label="答题用时">
                        {formatDuration(item.duration)}
                      </Descriptions.Item>
                      {item.score !== undefined && item.score !== null && (
                        <Descriptions.Item label="得分">
                          <Typography.Text strong style={{ color: '#4A90D9' }}>{item.score}</Typography.Text>
                        </Descriptions.Item>
                      )}
                      {item.quality_level && (
                        <Descriptions.Item label="答题质量">
                          <Tag color={item.quality_level === 'good' ? 'green' : item.quality_level === 'medium' ? 'orange' : 'red'}>
                            {item.quality_level === 'good' ? '良好' : item.quality_level === 'medium' ? '一般' : '较差'}
                          </Tag>
                        </Descriptions.Item>
                      )}
                      {item.comment && (
                        <Descriptions.Item label="评语" span={2}>
                          {item.comment}
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                  </div>
                )}
              </Card>
            );
          }}
        />
      )}
    </div>
  );
}
