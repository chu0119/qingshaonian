/**
 * Reusable report export component.
 *
 * Provides a button + modal for exporting reports with date range selection
 * and report type selection.
 */
import { useState } from 'react';
import { Button, Modal, DatePicker, Select, Space, message, Typography } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import client from '../../api/client';

const { RangePicker } = DatePicker;

interface ReportExportProps {
  reportTypes?: { value: string; label: string }[];
  defaultType?: string;
  buttonSize?: 'small' | 'middle' | 'large';
  buttonLabel?: string;
  compact?: boolean;
}

const defaultReportTypes = [
  { value: 'overview', label: '学校综合报表' },
  { value: 'risk', label: '风险预警报表' },
  { value: 'completion', label: '完成情况报表' },
];

export default function ReportExport({
  reportTypes = defaultReportTypes,
  defaultType = 'overview',
  buttonSize = 'middle',
  buttonLabel = '导出报表',
  compact = false,
}: ReportExportProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [reportType, setReportType] = useState(defaultType);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    if (!dateRange) {
      message.warning('请选择时间范围');
      return;
    }
    setExporting(true);
    try {
      const params = new URLSearchParams({
        report_type: reportType,
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
      });
      const response = await client.get(`/exports/report?${params.toString()}`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType}_report_${dayjs().format('YYYYMMDD_HHmm')}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
      setModalOpen(false);
    } catch {
      message.error('导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      {compact ? (
        <Button icon={<DownloadOutlined />} onClick={() => setModalOpen(true)} size={buttonSize}>
          {buttonLabel}
        </Button>
      ) : (
        <Button type="primary" icon={<DownloadOutlined />} onClick={() => setModalOpen(true)} size={buttonSize}>
          {buttonLabel}
        </Button>
      )}

      <Modal
        title="导出报表"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleExport}
        confirmLoading={exporting}
        okText="导出"
        cancelText="取消"
        width={480}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 16 }}>
          <div>
            <Typography.Text strong style={{ display: 'block', marginBottom: 6 }}>报表类型</Typography.Text>
            <Select
              value={reportType}
              onChange={setReportType}
              options={reportTypes}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <Typography.Text strong style={{ display: 'block', marginBottom: 6 }}>时间范围</Typography.Text>
            <RangePicker
              value={dateRange}
              onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
              presets={[
                { label: '最近7天', value: [dayjs().subtract(7, 'day'), dayjs()] },
                { label: '最近30天', value: [dayjs().subtract(30, 'day'), dayjs()] },
                { label: '最近90天', value: [dayjs().subtract(90, 'day'), dayjs()] },
                { label: '本学期', value: [dayjs().startOf('month'), dayjs()] },
              ]}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </Modal>
    </>
  );
}
