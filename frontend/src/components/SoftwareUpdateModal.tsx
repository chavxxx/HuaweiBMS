import React, { useState } from 'react'
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  DownloadCloud,
  ExternalLink,
  GitBranch,
  GitCommit,
  GitPullRequest,
  RefreshCw,
  ShieldCheck,
  Terminal,
  X,
} from 'lucide-react'
import { api } from '../services/api'
import type { UpdateCheckResult, UpdatePullResult, UserRole } from '../types'

interface SoftwareUpdateModalProps {
  isOpen: boolean
  onClose: () => void
  userRole: UserRole
  updateInfo: UpdateCheckResult | null
  loading: boolean
  onRefreshCheck: () => Promise<void>
}

export const SoftwareUpdateModal: React.FC<SoftwareUpdateModalProps> = ({
  isOpen,
  onClose,
  userRole,
  updateInfo,
  loading,
  onRefreshCheck,
}) => {
  const [pulling, setPulling] = useState(false)
  const [pullResult, setPullResult] = useState<UpdatePullResult | null>(null)
  const [pullError, setPullError] = useState<string | null>(null)

  if (!isOpen) return null

  const handlePullUpdate = async () => {
    if (userRole !== 'ADMINISTRATOR') return
    setPulling(true)
    setPullResult(null)
    setPullError(null)
    try {
      const res = await api.pullUpdate(userRole)
      setPullResult(res)
      // Re-check after pulling to update HEAD info
      await onRefreshCheck()
    } catch (err: any) {
      setPullError(err.message || 'Failed to pull update')
    } finally {
      setPulling(false)
    }
  }

  const formatTimestamp = (ts?: number) => {
    if (!ts) return 'Never'
    try {
      return new Date(ts * 1000).toLocaleString()
    } catch {
      return 'Unknown'
    }
  }

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Unknown'
    try {
      return new Date(isoString).toLocaleString()
    } catch {
      return isoString
    }
  }

  const isUpToDate = updateInfo?.status === 'UP_TO_DATE'
  const hasUpdate = updateInfo?.has_update || updateInfo?.status === 'UPDATE_AVAILABLE'
  const isError = updateInfo?.status === 'ERROR'
  const isGitRepo = updateInfo?.is_git_repo ?? true

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>Software Updates & Git Repository</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 font-bold">
                  GitHub Sync
                </span>
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                Repository: <span className="text-slate-300">chavxxx/HuaweiBMS</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 flex items-center justify-center transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* Status Hero Banner */}
          {loading ? (
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-center gap-3 font-mono text-xs text-slate-300">
              <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
              <div>
                <div className="font-bold text-slate-200">Checking GitHub for updates...</div>
                <div className="text-[11px] text-slate-400">
                  Querying api.github.com/repos/chavxxx/HuaweiBMS
                </div>
              </div>
            </div>
          ) : isError ? (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-600/50 flex items-start gap-3 font-mono text-xs text-rose-200">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-bold text-rose-300">Update Check Encountered an Error</div>
                <div className="text-[11px] text-rose-200/80">
                  {updateInfo?.error || 'Unable to connect to GitHub. Please check internet connection or rate limits.'}
                </div>
              </div>
            </div>
          ) : hasUpdate ? (
            <div className="p-4 rounded-xl bg-cyan-950/50 border border-cyan-500/60 flex items-start gap-3 font-mono text-xs text-cyan-200 shadow-lg shadow-cyan-950/50">
              <DownloadCloud className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5 animate-bounce" />
              <div className="space-y-1 flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-cyan-300 uppercase tracking-wider text-xs">
                    New Update Available!
                  </span>
                  <span className="text-[10px] bg-cyan-900/80 text-cyan-300 border border-cyan-700 px-2 py-0.5 rounded font-bold">
                    {updateInfo?.latest_version || updateInfo?.latest_commit?.substring(0, 7)}
                  </span>
                </div>
                <div className="text-[11px] text-cyan-200/80">
                  A newer release or commit is published to the remote repository.
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-600/50 flex items-center gap-3 font-mono text-xs text-emerald-300">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <div className="font-bold text-emerald-300">HuaweiBMS is Up to Date</div>
                <div className="text-[11px] text-emerald-400/80">
                  Your local installation matches the latest code on origin/main ({updateInfo?.current_commit?.substring(0, 7)}).
                </div>
              </div>
            </div>
          )}

          {/* Version & Commit Comparison Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
            {/* Local App Info */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800/80 pb-2">
                <span className="font-bold flex items-center gap-1.5 text-slate-300">
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                  Local Installation
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {updateInfo?.branch || 'main'}
                </span>
              </div>
              <div className="flex justify-between items-center pt-1">
                <span className="text-slate-400">Version:</span>
                <span className="font-bold text-slate-200 font-mono">
                  {updateInfo?.current_version || 'v1.0.4'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Local Commit:</span>
                <span className="text-cyan-400 font-bold font-mono">
                  {updateInfo?.current_commit ? updateInfo.current_commit.substring(0, 7) : '23fbe43'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Git Directory:</span>
                <span className="text-slate-300">
                  {isGitRepo ? 'Git Repository (.git)' : 'Standalone Bundle'}
                </span>
              </div>
            </div>

            {/* Remote GitHub Info */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800/80 pb-2">
                <span className="font-bold flex items-center gap-1.5 text-slate-300">
                  <GitCommit className="w-3.5 h-3.5 text-cyan-400" />
                  Remote GitHub Repo
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                  origin/main
                </span>
              </div>
              <div className="flex justify-between items-center pt-1">
                <span className="text-slate-400">Latest Release:</span>
                <span className="font-bold text-slate-200 font-mono">
                  {updateInfo?.latest_version || 'v1.0.4'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Remote Commit:</span>
                <span className="text-cyan-400 font-bold font-mono">
                  {updateInfo?.latest_commit ? updateInfo.latest_commit.substring(0, 7) : 'Latest'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Checked At:</span>
                <span className="text-slate-400 text-[11px]">
                  {formatTimestamp(updateInfo?.last_checked)}
                </span>
              </div>
            </div>
          </div>

          {/* Latest Remote Commit Details */}
          {updateInfo?.latest_commit_message && (
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800/80 pb-2">
                <span className="font-bold flex items-center gap-1.5 text-slate-300">
                  <GitPullRequest className="w-3.5 h-3.5 text-cyan-400" />
                  Latest Commit on GitHub
                </span>
                <span className="text-[10px] text-slate-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(updateInfo.latest_commit_date)}
                </span>
              </div>
              <div className="text-slate-200 text-xs bg-slate-900/90 p-2.5 rounded-lg border border-slate-800/80 leading-relaxed break-words font-mono">
                {updateInfo.latest_commit_message}
              </div>
              {updateInfo.release_notes && (
                <div className="pt-2">
                  <div className="text-[11px] text-slate-400 font-bold mb-1">Release Highlights:</div>
                  <div className="text-slate-300 text-[11px] whitespace-pre-wrap bg-slate-900/60 p-2 rounded border border-slate-800">
                    {updateInfo.release_notes}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Pull Result Banner */}
          {pullResult && (
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/60 font-mono text-xs space-y-2">
              <div className="flex items-center gap-2 text-emerald-300 font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>{pullResult.message}</span>
              </div>
              {pullResult.stdout && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-300 max-h-32 overflow-y-auto whitespace-pre-wrap">
                  {pullResult.stdout}
                </div>
              )}
            </div>
          )}

          {/* Pull Error Banner */}
          {pullError && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-600/60 font-mono text-xs text-rose-300 space-y-1">
              <div className="flex items-center gap-2 font-bold text-rose-200">
                <AlertCircle className="w-4 h-4 text-rose-400" />
                <span>Update Failed</span>
              </div>
              <p className="text-[11px] text-rose-300/80">{pullError}</p>
            </div>
          )}

          {/* Standalone packaging notice if applicable */}
          {!isGitRepo && (
            <div className="p-3 bg-amber-950/40 border border-amber-600/50 rounded-xl text-amber-300 text-xs font-mono flex items-start gap-2.5">
              <Terminal className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold">Standalone Executable Environment:</span>
                <p className="text-[11px] text-amber-300/80">
                  This instance is running as a packaged executable. To apply updates, please download the latest installer or executable package directly from the GitHub releases page.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer / Action Buttons */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => onRefreshCheck()}
              disabled={loading || pulling}
              className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium flex items-center gap-2 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
              <span>{loading ? 'Checking...' : 'Check Again'}</span>
            </button>

            <a
              href={updateInfo?.repo_url || 'https://github.com/chavxxx/HuaweiBMS'}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-mono font-medium flex items-center gap-1.5 transition"
            >
              <span>GitHub Repo</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <div className="flex items-center gap-3">
            {isGitRepo ? (
              <button
                onClick={handlePullUpdate}
                disabled={pulling || loading || userRole !== 'ADMINISTRATOR'}
                title={
                  userRole !== 'ADMINISTRATOR'
                    ? 'Administrator role required to pull git updates'
                    : 'Pull latest commits from origin/main'
                }
                className={`px-4 py-2 rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 shadow-lg ${
                  hasUpdate
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/20'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <DownloadCloud className={`w-3.5 h-3.5 ${pulling ? 'animate-bounce' : ''}`} />
                <span>
                  {pulling
                    ? 'Pulling Update...'
                    : hasUpdate
                    ? 'Pull & Apply Update'
                    : 'Force Git Pull'}
                </span>
              </button>
            ) : (
              <a
                href={updateInfo?.releases_url || 'https://github.com/chavxxx/HuaweiBMS/releases'}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold font-mono flex items-center gap-1.5 shadow-lg shadow-cyan-500/20"
              >
                <span>Download Installer</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </a>
            )}

            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono font-medium transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
