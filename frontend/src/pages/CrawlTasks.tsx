import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Tag,
  Empty,
  Spin,
  Typography,
  Button,
  Toast,
  Modal,
  Input,
  Select,
  Radio,
  RadioGroup,
  Collapsible,
} from "@douyinfe/semi-ui-19";
import {
  IconPlus,
  IconPlay,
  IconDelete,
  IconEdit,
  IconTick,
  IconClose,
  IconChevronDown,
  IconChevronUp,
} from "@douyinfe/semi-icons";
import client from "../api/client";
import SourceConfigForm from "../components/SourceConfigForm";
import "../styles/surfaces.css";

const { Text } = Typography;

interface SourceMeta {
  source_type: string;
  display_name: string;
  description: string;
  config_fields: Array<{
    key: string;
    label: string;
    field_type: string;
    required: boolean;
    default: unknown;
    description: string;
    options: { value: string; label: string }[] | null;
    min_value: number | null;
    max_value: number | null;
  }>;
  supported_schedules: string[];
}

interface CrawlTask {
  id: string;
  name: string;
  source_type: string;
  source_config: Record<string, unknown>;
  schedule_type: string;
  time_range: string;
  target_mode: string;
  target_collection_id: string | null;
  new_collection_prefix: string | null;
  duplicate_strategy: string;
  is_enabled: boolean;
  last_run_at: string | null;
  last_run_status: string | null;
  last_run_result: Record<string, unknown> | null;
  next_run_at: string | null;
}

interface TaskRun {
  id: string;
  status: string;
  result: Record<string, unknown> | null;
  collection_id: string | null;
  started_at: string | null;
  finished_at: string | null;
}

interface CollectionOption {
  id: string;
  title: string;
}
export default function CrawlTasks() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [sources, setSources] = useState<SourceMeta[]>([]);
  const [collections, setCollections] = useState<CollectionOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editTask, setEditTask] = useState<CrawlTask | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, TaskRun[]>>({});

  const loadData = useCallback(async () => {
    try {
      const [tasksRes, sourcesRes, colRes] = await Promise.all([
        client.get("/crawl-tasks"),
        client.get("/crawl-tasks/sources"),
        client.get("/collections"),
      ]);
      setTasks(tasksRes.data);
      setSources(sourcesRes.data);
      setCollections(
        colRes.data.map((c: { id: string; title: string }) => ({
          id: c.id,
          title: c.title,
        })),
      );
    } catch {
      Toast.error(t("crawl.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadRuns = async (taskId: string) => {
    try {
      const res = await client.get(`/crawl-tasks/${taskId}/runs`);
      setRuns((prev) => ({ ...prev, [taskId]: res.data }));
    } catch {
      /* ignore */
    }
  };

  const toggleExpand = (taskId: string) => {
    if (expandedTask === taskId) {
      setExpandedTask(null);
    } else {
      setExpandedTask(taskId);
      if (!runs[taskId]) loadRuns(taskId);
    }
  };

  const handleToggle = async (task: CrawlTask) => {
    try {
      const action = task.is_enabled ? "disable" : "enable";
      await client.post(`/crawl-tasks/${task.id}/${action}`);
      Toast.success(task.is_enabled ? t("crawl.disabled") : t("crawl.enabled"));
      loadData();
    } catch {
      Toast.error(t("crawl.enableFailed"));
    }
  };

  const handleRunNow = async (task: CrawlTask) => {
    try {
      await client.post(`/crawl-tasks/${task.id}/run-now`);
      Toast.success(t("crawl.runStarted"));
    } catch (err: any) {
      if (err.response?.status === 409) {
        Toast.warning(t("crawl.alreadyRunning"));
      } else {
        Toast.error(t("crawl.runFailed"));
      }
    }
  };

  const handleDelete = async (task: CrawlTask) => {
    try {
      await client.delete(`/crawl-tasks/${task.id}`);
      Toast.success(t("crawl.deleted"));
      loadData();
    } catch {
      Toast.error(t("crawl.deleteFailed"));
    }
  };

  const getSourceMeta = (sourceType: string) =>
    sources.find((s) => s.source_type === sourceType);

  const getCollectionName = (id: string | null) =>
    id ? collections.find((c) => c.id === id)?.title : null;

  const getTaskCollectionId = (task: CrawlTask): string | null =>
    task.target_collection_id ||
    (task.last_run_result?.collection_id as string | null) ||
    null;

  const formatDate = (iso: string | null) => {
    if (!iso) return t("crawl.never");
    return new Date(iso).toLocaleString();
  };

  const formatRunResult = (r: Record<string, unknown> | null) => {
    if (!r) return "";
    if (r.error) return String(r.error);
    const parts: string[] = [];
    if (r.new_papers)
      parts.push(t("crawl.newPapers", { count: Number(r.new_papers) }));
    if (r.skipped)
      parts.push(t("crawl.skippedPapers", { count: Number(r.skipped) }));
    if (r.updated)
      parts.push(t("crawl.updatedPapers", { count: Number(r.updated) }));
    return parts.join(", ");
  };

  const statusColor = (s: string) =>
    s === "success"
      ? "green"
      : s === "failed"
        ? "red"
        : s === "partial"
          ? "orange"
          : "grey";

  if (loading) {
    return (
      <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
    );
  }

  return (
    <div className="crawl-page">
      <div className="crawl-page-header">
        <div>
          <Typography.Title heading={3}>{t("crawl.title")}</Typography.Title>
          <Text>{t("crawl.subtitle")}</Text>
        </div>
        <Button
          icon={<IconPlus />}
          theme="solid"
          onClick={() => setShowCreate(true)}
        >
          {t("crawl.newTask")}
        </Button>
      </div>

      {tasks.length === 0 ? (
        <div className="crawl-empty-state">
          <Empty
            title={t("crawl.noTasks")}
            description={t("crawl.noTasksHint")}
          />
        </div>
      ) : (
        <section className="crawl-task-list" aria-label={t("crawl.title")}>
          <div className="crawl-task-list-header">
            <span>{t("crawl.taskCount", { count: tasks.length })}</span>
            <span>
              {t("crawl.enabledCount", {
                count: tasks.filter((task) => task.is_enabled).length,
              })}
            </span>
          </div>
          {tasks.map((task) => {
            const sourceMeta = getSourceMeta(task.source_type);
            const colId = getTaskCollectionId(task);
            const colName = getCollectionName(colId);
            const isExpanded = expandedTask === task.id;
            const taskRuns = runs[task.id] || [];
            const resultText = formatRunResult(task.last_run_result);

            return (
              <article key={task.id} className="crawl-task-record">
                <div className="crawl-task-main">
                  <div className="crawl-task-heading">
                    <div>
                      <div className="crawl-task-kicker">
                        <span>
                          {sourceMeta?.display_name || task.source_type}
                        </span>
                        <span>{t(`crawl.${task.schedule_type}`)}</span>
                      </div>
                      <h2>{task.name}</h2>
                    </div>
                    <div className="crawl-task-statuses">
                      <span
                        className={`crawl-status ${task.is_enabled ? "is-success" : "is-muted"}`}
                      >
                        <i aria-hidden="true" />
                        {task.is_enabled
                          ? t("crawl.status.enabled")
                          : t("crawl.status.disabled")}
                      </span>
                      {task.last_run_status && (
                        <span
                          className={`crawl-status is-${task.last_run_status}`}
                        >
                          <i aria-hidden="true" />
                          {t(`crawl.status.${task.last_run_status}`)}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="crawl-task-facts">
                    <div>
                      <span>{t("crawl.targetMode")}</span>
                      {colId ? (
                        <button
                          type="button"
                          onClick={() => navigate(`/collections/${colId}`)}
                        >
                          {colName || colId}
                        </button>
                      ) : (
                        <strong>
                          {task.new_collection_prefix || t("crawl.createNew")}
                        </strong>
                      )}
                    </div>
                    <div>
                      <span>{t("crawl.lastRun")}</span>
                      <strong>{formatDate(task.last_run_at)}</strong>
                    </div>
                    <div>
                      <span>{t("crawl.nextRun")}</span>
                      <strong>{formatDate(task.next_run_at)}</strong>
                    </div>
                    <div>
                      <span>{t("crawl.lastResult")}</span>
                      <strong
                        className={
                          task.last_run_result?.error ? "is-error" : ""
                        }
                      >
                        {task.last_run_result?.error ===
                        "target_collection_deleted"
                          ? t("crawl.targetDeleted")
                          : resultText || "—"}
                      </strong>
                    </div>
                  </div>

                  <div className="crawl-task-toolbar">
                    <div className="crawl-task-actions">
                      <Button
                        icon={<IconPlay />}
                        size="small"
                        theme="light"
                        onClick={() => handleRunNow(task)}
                      >
                        {t("crawl.runNow")}
                      </Button>
                      <Button
                        icon={<IconEdit />}
                        size="small"
                        theme="borderless"
                        type="tertiary"
                        onClick={() => setEditTask(task)}
                      >
                        {t("crawl.edit")}
                      </Button>
                      <Button
                        icon={task.is_enabled ? <IconClose /> : <IconTick />}
                        size="small"
                        theme="borderless"
                        type={task.is_enabled ? "warning" : "primary"}
                        onClick={() => handleToggle(task)}
                      >
                        {task.is_enabled
                          ? t("crawl.disable")
                          : t("crawl.enable")}
                      </Button>
                      <Button
                        icon={<IconDelete />}
                        size="small"
                        theme="borderless"
                        type="danger"
                        aria-label={`${t("crawl.delete")} ${task.name}`}
                        title={`${t("crawl.delete")} ${task.name}`}
                        onClick={() =>
                          Modal.confirm({
                            title: t("crawl.deleteConfirm", {
                              name: task.name,
                            }),
                            onOk: () => handleDelete(task),
                          })
                        }
                      />
                    </div>
                    <button
                      className="crawl-history-toggle"
                      type="button"
                      aria-expanded={isExpanded}
                      onClick={() => toggleExpand(task.id)}
                    >
                      {t("crawl.runHistory")}
                      {isExpanded ? (
                        <IconChevronUp size="small" />
                      ) : (
                        <IconChevronDown size="small" />
                      )}
                    </button>
                  </div>
                </div>

                <Collapsible isOpen={isExpanded}>
                  <div className="crawl-run-history">
                    {taskRuns.length === 0 ? (
                      <Text type="tertiary" size="small">
                        {t("crawl.noRuns")}
                      </Text>
                    ) : (
                      taskRuns.map((run) => (
                        <div key={run.id} className="crawl-run-row">
                          <Tag color={statusColor(run.status)} size="small">
                            {run.status}
                          </Tag>
                          <span>{formatRunResult(run.result) || "—"}</span>
                          {run.collection_id ? (
                            <button
                              type="button"
                              onClick={() =>
                                navigate(`/collections/${run.collection_id}`)
                              }
                            >
                              {getCollectionName(run.collection_id) ||
                                run.collection_id}
                            </button>
                          ) : (
                            <span />
                          )}
                          <time>{formatDate(run.started_at)}</time>
                        </div>
                      ))
                    )}
                  </div>
                </Collapsible>
              </article>
            );
          })}
        </section>
      )}

      <TaskFormModal
        visible={showCreate || !!editTask}
        task={editTask}
        sources={sources}
        collections={collections}
        onClose={() => {
          setShowCreate(false);
          setEditTask(null);
        }}
        onSuccess={() => {
          setShowCreate(false);
          setEditTask(null);
          loadData();
        }}
      />
    </div>
  );
}

function TaskFormModal({
  visible,
  task,
  sources,
  collections,
  onClose,
  onSuccess,
}: {
  visible: boolean;
  task: CrawlTask | null;
  sources: SourceMeta[];
  collections: CollectionOption[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useTranslation();
  const isEdit = !!task;

  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [sourceConfig, setSourceConfig] = useState<Record<string, unknown>>({});
  const [scheduleType, setScheduleType] = useState("daily");
  const [timeRange, setTimeRange] = useState("1d");
  const [targetMode, setTargetMode] = useState("append");
  const [targetCollectionId, setTargetCollectionId] = useState<string>("");
  const [newCollectionPrefix, setNewCollectionPrefix] = useState("");
  const [duplicateStrategy, setDuplicateStrategy] = useState("skip");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (task) {
      setName(task.name);
      setSourceType(task.source_type);
      setSourceConfig(task.source_config);
      setScheduleType(task.schedule_type);
      setTimeRange(task.time_range);
      setTargetMode(task.target_mode);
      setTargetCollectionId(task.target_collection_id || "");
      setNewCollectionPrefix(task.new_collection_prefix || "");
      setDuplicateStrategy(task.duplicate_strategy);
    } else {
      setName("");
      setSourceType(sources[0]?.source_type || "");
      setSourceConfig({});
      setScheduleType("daily");
      setTimeRange("1d");
      setTargetMode("append");
      setTargetCollectionId("");
      setNewCollectionPrefix("");
      setDuplicateStrategy("skip");
    }
  }, [task, sources, visible]);

  const selectedSource = sources.find((s) => s.source_type === sourceType);

  const handleSubmit = async () => {
    if (!name.trim()) {
      Toast.warning(t("crawl.taskNameRequired"));
      return;
    }
    if (targetMode === "append" && !targetCollectionId) {
      Toast.warning(t("crawl.selectCollection"));
      return;
    }
    if (targetMode === "create_new" && !newCollectionPrefix.trim()) {
      Toast.warning(t("crawl.collectionPrefix"));
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        name,
        source_type: sourceType,
        source_config: sourceConfig,
        schedule_type: scheduleType,
        time_range: timeRange,
        target_mode: targetMode,
        target_collection_id:
          targetMode === "append" && targetCollectionId
            ? targetCollectionId
            : null,
        new_collection_prefix:
          targetMode === "create_new" && newCollectionPrefix
            ? newCollectionPrefix
            : null,
        duplicate_strategy: duplicateStrategy,
      };

      if (isEdit) {
        await client.put(`/crawl-tasks/${task!.id}`, payload);
        Toast.success(t("crawl.updateSuccess"));
      } else {
        await client.post("/crawl-tasks", payload);
        Toast.success(t("crawl.createSuccess"));
      }
      onSuccess();
    } catch {
      Toast.error(isEdit ? t("crawl.updateFailed") : t("crawl.createFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const isMobile = typeof window !== "undefined" && window.innerWidth < 640;

  return (
    <Modal
      className="task-form-dialog"
      title={isEdit ? t("crawl.editTitle") : t("crawl.createTitle")}
      visible={visible}
      onCancel={onClose}
      footer={
        <div className="task-form-actions">
          <Button theme="borderless" onClick={onClose}>
            {t("crawl.cancel")}
          </Button>
          <Button theme="solid" loading={submitting} onClick={handleSubmit}>
            {isEdit ? t("crawl.save") : t("crawl.create")}
          </Button>
        </div>
      }
      fullScreen={isMobile}
      width={isMobile ? undefined : 560}
      closeOnEsc
    >
      <div className="task-form">
        <section className="task-form-section">
          <h3>{t("crawl.basics")}</h3>
          <div className="task-form-fields">
            <div>
              <label className="form-label">{t("crawl.taskName")}</label>
              <Input
                value={name}
                onChange={setName}
                placeholder={t("crawl.taskNamePlaceholder")}
              />
            </div>

            {!isEdit && (
              <div>
                <label className="form-label">{t("crawl.selectSource")}</label>
                <Select
                  value={sourceType}
                  onChange={(val) => {
                    setSourceType(val as string);
                    setSourceConfig({});
                  }}
                  optionList={sources.map((s) => ({
                    value: s.source_type,
                    label: s.display_name,
                  }))}
                />
              </div>
            )}

            {selectedSource && selectedSource.config_fields.length > 0 && (
              <div>
                <label className="form-label">{t("crawl.configSource")}</label>
                <SourceConfigForm
                  fields={selectedSource.config_fields}
                  value={sourceConfig}
                  onChange={setSourceConfig}
                />
              </div>
            )}
          </div>
        </section>

        <section className="task-form-section">
          <h3>{t("crawl.automation")}</h3>
          <div>
            <label className="form-label">{t("crawl.schedule")}</label>
            <RadioGroup
              className="task-choice-group"
              value={scheduleType}
              onChange={(e) => setScheduleType(e.target.value)}
              direction="horizontal"
            >
              <Radio value="once">{t("crawl.once")}</Radio>
              <Radio value="daily">{t("crawl.daily")}</Radio>
              <Radio value="weekly">{t("crawl.weekly")}</Radio>
              <Radio value="monthly">{t("crawl.monthly")}</Radio>
            </RadioGroup>
          </div>
        </section>

        <section className="task-form-section">
          <h3>{t("crawl.destination")}</h3>
          <div className="task-form-fields">
            <div>
              <label className="form-label">{t("crawl.targetMode")}</label>
              <RadioGroup
                className="task-choice-group is-vertical"
                value={targetMode}
                onChange={(e) => setTargetMode(e.target.value)}
              >
                <Radio value="append">{t("crawl.append")}</Radio>
                <Radio value="create_new">{t("crawl.createNew")}</Radio>
              </RadioGroup>
            </div>

            {targetMode === "append" && (
              <div>
                <label className="form-label">
                  {t("crawl.selectCollection")}
                </label>
                <Select
                  value={targetCollectionId}
                  onChange={(val) => setTargetCollectionId(val as string)}
                  optionList={collections.map((c) => ({
                    value: c.id,
                    label: c.title,
                  }))}
                  filter
                />
              </div>
            )}

            {targetMode === "create_new" && (
              <div>
                <label className="form-label">
                  {t("crawl.collectionPrefix")}
                </label>
                <Input
                  value={newCollectionPrefix}
                  onChange={setNewCollectionPrefix}
                  placeholder={t("crawl.collectionPrefixPlaceholder")}
                />
              </div>
            )}
          </div>
        </section>

        <section className="task-form-section">
          <h3>{t("crawl.importBehavior")}</h3>
          <div>
            <label className="form-label">{t("crawl.duplicateStrategy")}</label>
            <RadioGroup
              className="task-choice-group"
              value={duplicateStrategy}
              onChange={(e) => setDuplicateStrategy(e.target.value)}
              direction="horizontal"
            >
              <Radio value="skip">{t("crawl.skip")}</Radio>
              <Radio value="update">{t("crawl.update")}</Radio>
            </RadioGroup>
          </div>
        </section>
      </div>
    </Modal>
  );
}
