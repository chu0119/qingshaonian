import { useState, useEffect, useCallback } from 'react';
import { Input, Select, Typography, Card, Table, Button, Space, message, Row, Col } from 'antd';
import { SearchOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

export default function StudentProfilePage() {
  const navigate = useNavigate();
  const [schools, setSchools] = useState<{ value: number; label: string }[]>([]);
  const [grades, setGrades] = useState<{ value: number; label: string }[]>([]);
  const [classes, setClasses] = useState<{ value: number; label: string }[]>([]);
  const [schoolId, setSchoolId] = useState<number | undefined>();
  const [gradeId, setGradeId] = useState<number | undefined>();
  const [classId, setClassId] = useState<number | undefined>();
  const [keyword, setKeyword] = useState('');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searched, setSearched] = useState(false);

  // 加载学校列表
  useEffect(() => {
    client.get('/platform/schools', { params: { page: 1, page_size: 200 } })
      .then(r => setSchools((r.data.data.items || []).map((s: any) => ({ value: s.id, label: s.name }))))
      .catch(() => {});
  }, []);

  // 学校变化时加载年级列表
  useEffect(() => {
    if (!schoolId) { setGrades([]); setClasses([]); setGradeId(undefined); setClassId(undefined); return; }
    client.get('/platform/grades', { params: { school_id: schoolId } })
      .then(r => setGrades((r.data.data || []).map((g: any) => ({ value: g.id, label: g.name }))))
      .catch(() => setGrades([]));
    setClasses([]);
    setGradeId(undefined);
    setClassId(undefined);
  }, [schoolId]);

  // 年级变化时加载班级列表
  useEffect(() => {
    if (!gradeId) { setClasses([]); setClassId(undefined); return; }
    client.get('/platform/classes', { params: { grade_id: gradeId } })
      .then(r => setClasses((r.data.data || []).map((c: any) => ({ value: c.id, label: c.name }))))
      .catch(() => setClasses([]));
    setClassId(undefined);
  }, [gradeId]);

  const fetchData = useCallback(async (p = page, sk = schoolId, gd = gradeId, cls = classId, kw = keyword) => {
    setLoading(true); setSearched(true);
    try {
      const params: Record<string, any> = { page: p, page_size: 20 };
      if (sk) params.school_id = sk;
      if (gd) params.grade_id = gd;
      if (cls) params.class_id = cls;
      if (kw.trim()) params.keyword = kw.trim();
      const r = await client.get('/platform/students', { params });
      setData(r.data.data?.items || []);
      setTotal(r.data.data?.total || 0);
      setPage(p);
    } catch {
      message.error('查询失败');
    } finally { setLoading(false); }
  }, [page, schoolId, gradeId, classId, keyword]);

  const resetFilters = () => {
    setSchoolId(undefined);
    setGradeId(undefined);
    setClassId(undefined);
    setKeyword('');
    setPage(1);
    setData([]);
    setTotal(0);
    setSearched(false);
  };

  const columns = [
    { title: '姓名', dataIndex: 'student_name', key: 'student_name', width: 90, ellipsis: true },
    { title: '学号', dataIndex: 'student_no', key: 'student_no', width: 110, ellipsis: true },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 130, ellipsis: true },
    { title: '年级', dataIndex: 'grade_name', key: 'grade_name', width: 70 },
    { title: '班级', dataIndex: 'class_name', key: 'class_name', width: 70 },
    { title: '性别', dataIndex: 'gender', key: 'gender', width: 50 },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 110, ellipsis: true },
    {
      title: '操作', key: 'action', width: 70, fixed: 'right' as const,
      render: (_: any, r: any) => (
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={() => navigate(`/platform/students/${r.id}`)}>查看</Button>
      ),
    },
  ];

  const hasFilter = schoolId || gradeId || classId || keyword.trim();

  return (
    <div>
      <Typography.Title level={4}>学生档案</Typography.Title>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} sm={12} md={6} lg={5}>
            <Select placeholder="选择学校" allowClear style={{ width: '100%' }}
              value={schoolId} onChange={v => setSchoolId(v || undefined)}
              options={schools} showSearch optionFilterProp="label" />
          </Col>
          <Col xs={24} sm={12} md={5} lg={4}>
            <Select placeholder="选择年级" allowClear style={{ width: '100%' }}
              value={gradeId} onChange={v => setGradeId(v || undefined)}
              options={grades} disabled={!schoolId} />
          </Col>
          <Col xs={24} sm={12} md={5} lg={4}>
            <Select placeholder="选择班级" allowClear style={{ width: '100%' }}
              value={classId} onChange={v => setClassId(v || undefined)}
              options={classes} disabled={!gradeId} />
          </Col>
          <Col xs={24} sm={12} md={6} lg={5}>
            <Input.Search placeholder="姓名/学号/身份证" value={keyword}
              onChange={e => setKeyword(e.target.value)}
              onSearch={() => fetchData(1, schoolId, gradeId, classId, keyword)}
              enterButton={<><SearchOutlined /> 搜索</>} />
          </Col>
          <Col xs={24} sm={12} md={2} lg={2}>
            {hasFilter && (
              <Button icon={<ReloadOutlined />} onClick={resetFilters}>重置</Button>
            )}
          </Col>
        </Row>
      </Card>
      {searched && (
        <Table rowKey="id" dataSource={data} columns={columns} loading={loading} scroll={{ x: 1000 }}
          pagination={{ current: page, total, pageSize: 20, onChange: (p) => fetchData(p), showTotal: t => `共 ${t} 条` }} />
      )}
    </div>
  );
}
