import {
  Database,
  Eye,
  EyeOff,
  FilePlus2,
  FolderOpen,
  Plus,
  RotateCcw,
  Save,
  Trash2,
} from "lucide-react";
import type { SourceInfo } from "../../../ipc/protocol";

type SourceSidebarProps = {
  sources: SourceInfo[];
  /** Input file count only (excludes Combined). */
  inputFileCount: number;
  hasF3: boolean;
  hasFiles: boolean;
  busy: boolean;
  combinedVisible: boolean;
  onOpenFiles: () => void;
  onRemoveFile: (index: number, name: string) => void;
  onToggleCombinedVisibility: () => void;
  onSaveProject: () => void;
  onOpenProject: () => void;
  onResetWorkspace: () => void;
};

export function SourceSidebar({
  sources,
  inputFileCount,
  hasF3,
  hasFiles,
  busy,
  combinedVisible,
  onOpenFiles,
  onRemoveFile,
  onToggleCombinedVisibility,
  onSaveProject,
  onOpenProject,
  onResetWorkspace,
}: SourceSidebarProps) {
  return (
    <aside className="source-sidebar">
      <div className="sidebar-heading">
        <div>
          <span className="section-kicker">프로젝트</span>
          <h2>데이터 파일</h2>
        </div>
        <button
          type="button"
          className="icon-button accent"
          onClick={onOpenFiles}
          disabled={busy}
          aria-label="파일 추가"
        >
          <Plus size={16} />
        </button>
      </div>

      <button
        type="button"
        className="source-drop-card"
        onClick={onOpenFiles}
        disabled={busy}
      >
        <span className="drop-icon">
          <FilePlus2 size={18} />
        </span>
        <span>
          <strong>데이터 불러오기</strong>
          <small>TXT, CSV, Excel</small>
        </span>
      </button>

      <div className="source-count-row">
        <span>파일 {inputFileCount}개</span>
        {hasF3 ? <span className="mini-badge">F3 사용 가능</span> : null}
      </div>

      <div className="source-list">
        {sources.length === 0 ? (
          <div className="source-empty">
            <Database size={18} />
            <p>아직 불러온 데이터가 없습니다</p>
            <span>측정 파일을 추가해 분석을 시작하세요.</span>
          </div>
        ) : (
          sources.map((source) => (
            <div className="source-item" key={`${source.index}-${source.name}`}>
              <span className="source-index">
                {String(source.index + 1).padStart(2, "0")}
              </span>
              <div className="source-copy">
                <strong title={source.path ?? source.name}>{source.name}</strong>
                <span>
                  {source.is_combined
                    ? "결합 데이터"
                    : source.has_f3
                      ? "F1 · F2 · F3"
                      : "F1 · F2"}
                </span>
              </div>
              {source.is_combined ? (
                <button
                  type="button"
                  className="icon-button"
                  onClick={onToggleCombinedVisibility}
                  disabled={busy}
                  aria-pressed={combinedVisible}
                  aria-label={combinedVisible ? "Combined 데이터 숨기기" : "Combined 데이터 표시"}
                  title={combinedVisible ? "Combined 데이터 숨기기" : "Combined 데이터 표시"}
                >
                  {combinedVisible ? <Eye size={14} /> : <EyeOff size={14} />}
                </button>
              ) : (
                <button
                  type="button"
                  className="icon-button danger"
                  onClick={() => onRemoveFile(source.index, source.name)}
                  disabled={busy}
                  aria-label={`${source.name} 삭제`}
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))
        )}
      </div>

      <div className="sidebar-project-actions">
        <button
          type="button"
          className="project-link"
          onClick={onSaveProject}
          disabled={busy || !hasFiles}
        >
          <Save size={15} />
          프로젝트 저장
        </button>
        <button
          type="button"
          className="project-link"
          onClick={onOpenProject}
          disabled={busy}
        >
          <FolderOpen size={15} />
          프로젝트 열기
        </button>
        <button
          type="button"
          className="project-link muted"
          onClick={onResetWorkspace}
          disabled={busy}
        >
          <RotateCcw size={14} />
          초기화
        </button>
      </div>
    </aside>
  );
}
