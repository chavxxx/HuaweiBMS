import React, { useState } from 'react'
import {
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  Lock,
  RotateCw,
  ShieldAlert,
  X,
  XCircle,
} from 'lucide-react'
import { api } from '../services/api'
import type { ParameterItem, UserRole } from '../types'

interface GuardedWriteModalProps {
  parameter: ParameterItem | null
  userRole: UserRole
  onClose: () => void
  onSuccess: () => void
}

interface StepItem {
  step_number: number
  title: string
  status: 'PENDING' | 'COMPLETED' | 'FAILED'
  details: string
}

export const GuardedWriteModal: React.FC<GuardedWriteModalProps> = ({
  parameter,
  userRole,
  onClose,
  onSuccess,
}) => {
  if (!parameter) return null

  const [inputVal, setInputVal] = useState<string>(String(parameter.current_raw ?? ''))
  const [confirmed, setConfirmed] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [steps, setSteps] = useState<StepItem[]>([])
  const [writeResult, setWriteResult] = useState<any | null>(null)

  const numVal = parseFloat(inputVal)
  const isNaNVal = isNaN(numVal)
  const isBelowMin = parameter.min_value !== null && !isNaNVal && numVal < parameter.min_value
  const isAboveMax = parameter.max_value !== null && !isNaNVal && numVal > parameter.max_value
  const isValidRange = !isNaNVal && !isBelowMin && !isAboveMax
  const isUnchanged = parameter.current_raw !== null && numVal === parameter.current_raw

  const handleExecute = async () => {
    if (!isValidRange || !confirmed || executing) return
    setExecuting(true)
    setErrorMsg(null)
    setSteps([])
    setWriteResult(null)

    try {
      const res = await api.writeParameter({
        address: parameter.address,
        new_value: numVal,
        user_role: userRole,
        operator_confirmed: true,
      })

      setSteps(res.steps || [])
      setWriteResult(res)
      if (res.success) {
        onSuccess()
      } else {
        setErrorMsg(res.message || 'Write execution rejected')
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error executing write')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>10-Step Guarded Parameter Write</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  Reg: {parameter.address} (0x{parameter.address.toString(16).toUpperCase()})
                </span>
              </h2>
              <p className="text-xs text-slate-400">{parameter.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono">
          {/* Parameter Details Table */}
          <div className="grid grid-cols-2 gap-3 bg-slate-950/80 p-3.5 rounded-lg border border-slate-800">
            <div>
              <span className="text-slate-500">Allowed Range:</span>
              <div className="text-slate-200 font-semibold">
                [{parameter.min_value ?? 'N/A'} .. {parameter.max_value ?? 'N/A'}] {parameter.unit}
              </div>
            </div>
            <div>
              <span className="text-slate-500">Access Mode:</span>
              <div className="text-emerald-400 font-semibold uppercase">{parameter.access_mode}</div>
            </div>
            <div className="col-span-2">
              <span className="text-slate-500">Operational Effect:</span>
              <div className="text-slate-300 font-sans mt-0.5">{parameter.description}</div>
            </div>
            <div className="col-span-2 text-[11px]">
              <span className="text-slate-500">Source Documentation:</span>
              <div className="text-cyan-400">{parameter.source_doc}</div>
            </div>
          </div>

          {/* Value Edit & Diff Comparison */}
          <div className="space-y-3">
            <label className="block text-slate-300 font-bold">Step 3 & 4: Enter New Value & Validate</label>
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <input
                  type="number"
                  step="any"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  disabled={executing || writeResult?.success}
                  className={`w-full bg-slate-950 border rounded-lg px-3.5 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:ring-1 ${
                    isValidRange
                      ? 'border-emerald-600 focus:ring-emerald-500'
                      : 'border-rose-600 focus:ring-rose-500'
                  }`}
                  placeholder="Enter numeric value..."
                />
                <span className="absolute right-3 top-2.5 text-xs text-slate-500 font-bold">
                  {parameter.unit}
                </span>
              </div>

              {/* Status Indicator */}
              <div className="w-36 text-center text-[11px] font-semibold">
                {isBelowMin && <span className="text-rose-400">Below Min Limit</span>}
                {isAboveMax && <span className="text-rose-400">Above Max Limit</span>}
                {isNaNVal && <span className="text-rose-400">Invalid Number</span>}
                {isUnchanged && <span className="text-slate-400">Value Unchanged</span>}
                {isValidRange && !isUnchanged && (
                  <span className="text-emerald-400 flex items-center justify-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Valid Bounds
                  </span>
                )}
              </div>
            </div>

            {/* Before / After Diff */}
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center justify-around text-center">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Current Value</div>
                <div className="text-sm font-bold text-slate-300 font-mono">
                  {parameter.current_formatted}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-cyan-400" />
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Proposed Target</div>
                <div className="text-sm font-bold text-cyan-400 font-mono">
                  {isNaNVal ? 'N/A' : `${numVal} ${parameter.unit}`}
                </div>
              </div>
            </div>
          </div>

          {/* Stepper Progress View (Shown during / after execution) */}
          {steps.length > 0 && (
            <div className="border border-slate-800 rounded-lg p-3 bg-slate-950/90 space-y-2">
              <div className="text-xs font-bold text-slate-300 flex items-center justify-between">
                <span>Verification & Execution Stepper</span>
                <span className="text-[11px] font-normal text-slate-400">
                  {steps.filter((s) => s.status === 'COMPLETED').length} / 10 Completed
                </span>
              </div>
              <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                {steps.map((st) => (
                  <div
                    key={st.step_number}
                    className="flex items-start gap-2 text-[11px] py-1 border-b border-slate-900"
                  >
                    {st.status === 'COMPLETED' ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    ) : st.status === 'FAILED' ? (
                      <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                    ) : (
                      <RotateCw className="w-3.5 h-3.5 text-amber-400 animate-spin shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="font-semibold text-slate-200">
                        Step {st.step_number}: {st.title}
                      </div>
                      <div className="text-slate-400 text-[10px]">{st.details}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Confirmation Checkbox */}
          {!writeResult?.success && (
            <div className="p-3 bg-amber-950/20 border border-amber-900/60 rounded-lg space-y-2">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  disabled={executing || !isValidRange}
                  className="mt-0.5 w-4 h-4 rounded text-cyan-600 focus:ring-0 bg-slate-900 border-slate-700"
                />
                <span className="text-[11px] text-amber-200 leading-tight">
                  I confirm that I am authorized as <strong>{userRole}</strong>, have reviewed the
                  operational limits in official documentation, and acknowledge that this write modifies
                  active battery firmware parameters.
                </span>
              </label>
            </div>
          )}

          {/* Result Alert */}
          {writeResult?.success && (
            <div className="p-3 bg-emerald-950/40 border border-emerald-500/60 rounded-lg text-emerald-300 flex items-start gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-xs">Write Verified Successfully!</div>
                <div className="text-[11px] text-emerald-200 mt-0.5">
                  Hardware read-back confirmed parameter updated to{' '}
                  <strong>
                    {writeResult.verified_value} {parameter.unit}
                  </strong>
                  . Audit log #{writeResult.audit_id} generated.
                </div>
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 bg-rose-950/40 border border-rose-500/60 rounded-lg text-rose-300 flex items-start gap-2.5">
              <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-xs">Write Execution Blocked / Failed</div>
                <div className="text-[11px] text-rose-200 mt-0.5">{errorMsg}</div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="text-[11px] text-slate-500 font-mono">
            Requires: Administrator role & verified allowlist
          </div>
          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition"
            >
              {writeResult?.success ? 'Close' : 'Cancel'}
            </button>
            {!writeResult?.success && (
              <button
                onClick={handleExecute}
                disabled={!isValidRange || !confirmed || executing}
                className={`px-5 py-2 rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 ${
                  isValidRange && confirmed && !executing
                    ? 'bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-400 hover:to-rose-500 text-white shadow-lg shadow-amber-500/20'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                }`}
              >
                {executing ? (
                  <>
                    <RotateCw className="w-4 h-4 animate-spin" />
                    <span>Executing Steps...</span>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="w-4 h-4" />
                    <span>Execute 10-Step Write</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
