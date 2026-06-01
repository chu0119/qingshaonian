import { useState } from 'react';
import { Input, Select, Typography, Card, Table, Button, Space, message } from 'antd';
import { SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

export default function StudentProfilePage() {
  const navigate = useNavigate();
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [schoolId, setSchoolId] = useState<number | undefined>();
  const [keyword, setKeyword] = useState('');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searched, setSearched] = useState(false);

  // 加载学校列表
  useState(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  });

  const fetchData = async (p = page) => {
    if (!keyword.trim() && !schoolId) { message.warning('请输入学生姓名或选择学校'); return; }
    setLoading(true); setSearched(true);
    try {
      const params: Record<string, any> = { page: p, page_size: 20 };
      if (schoolId) params.school_id = schoolId;
      if (keyword.trim()) params.keyword = keyword.trim();
      const r = await client.get('/platform/students', { params });
      setData(r.data.data?.items || []);
      setTotal(r.data.data?.total || 0);
      setPage(p);
    } catch {
      message.error('查询失败');
    } finally { setLoading(false); }
  };

  const columns = [
    { title: '姓名', dataIndex: 'student_name', key: 'student_name', width: 100 },
    { title: '学号', dataIndex: 'student_no', key: 'student_no', width: 120 },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 150, ellipsis: true },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name', width: 80 },
    { title: '班级', dataIndex: 'class_name', key: 'class_name', width: 80 },
    { title: '性别', dataIndex: 'gender', key: 'gender', width: 60 },
    {
      title: '操作', key: 'action', width: 80,
      render: (_: any, r: any) => (
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={() => navigate(`/platform/students/${r.id}`)}>查看</Button>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>学生档案</Typography.Title>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select placeholder="选择学校" allowClear style={{ width: 200 }}
            value={schoolId} onChange={setSchoolId}
            options={schools} showSearch optionFilterProp="label" />
          <Input.Search placeholder="输入学生姓名或学号" style={{ width: 240 }}
            value={keyword} onChange={e => setKeyword(e.target.value)}
            onSearch={() => fetchData(1)} enterButton={<><SearchOutlined /> 搜索</>} />
        </Space>
      </Card>
      {searched && (
        <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 'max-content' }}
          pagination={{ current: page, total, pageSize: 20, onChange: (p) => fetchData(p), showTotal: t => `共 ${t} 条` }} />
      )}
    </div>
  );
}
