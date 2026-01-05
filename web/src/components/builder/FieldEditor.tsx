import { useState, useEffect } from 'react';
import { FormField, FieldType } from '../../types/form';
import { X, Plus, Trash2 } from 'lucide-react';

interface FieldEditorProps {
  field?: FormField; // If undefined, we are adding new
  isOpen: boolean;
  onClose: () => void;
  onSave: (field: FormField) => void;
}

const FIELD_TYPES: { type: FieldType; label: string }[] = [
  { type: 'text', label: 'Short Text' },
  { type: 'number', label: 'Number' },
  { type: 'email', label: 'Email Address' },
  { type: 'phone', label: 'Phone Number' },
  { type: 'date', label: 'Date' },
  { type: 'select', label: 'Dropdown Selection' },
  { type: 'boolean', label: 'Yes/No' },
];

export const FieldEditor = ({ field, isOpen, onClose, onSave }: FieldEditorProps) => {
  const [formData, setFormData] = useState<Partial<FormField>>({
    label: '',
    type: 'text',
    description: '',
    required: true,
    options: []
  });

  useEffect(() => {
    if (isOpen) {
      if (field) {
        setFormData({ ...field });
      } else {
        setFormData({
          id: Math.random().toString(36).substr(2, 9),
          label: '',
          type: 'text',
          description: '',
          required: true,
          options: []
        });
      }
    }
  }, [isOpen, field]);

  if (!isOpen) return null;

  const handleSave = () => {
    if (!formData.label || !formData.description) return; // Simple validation
    onSave(formData as FormField);
    onClose();
  };

  const addOption = () => {
    const newOptions = [...(formData.options || [])];
    newOptions.push({ label: '', value: '' });
    setFormData({ ...formData, options: newOptions });
  };

  const updateOption = (index: number, key: 'label' | 'value', val: string) => {
    const newOptions = [...(formData.options || [])];
    newOptions[index] = { ...newOptions[index], [key]: val };
    // Auto-fill value if empty when typing label
    if (key === 'label' && !newOptions[index].value) {
      newOptions[index].value = val.toLowerCase().replace(/\s+/g, '_');
    }
    setFormData({ ...formData, options: newOptions });
  };

  const removeOption = (index: number) => {
    const newOptions = [...(formData.options || [])];
    newOptions.splice(index, 1);
    setFormData({ ...formData, options: newOptions });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center px-6 py-4 border-b border-gray-100 bg-gray-50/50">
          <h3 className="text-lg font-bold text-gray-900">
            {field ? 'Edit Field' : 'Add New Field'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Label */}
          <div className="space-y-1">
            <label className="text-sm font-semibold text-gray-700">Field Label <span className="text-red-500">*</span></label>
            <input
              autoFocus
              type="text"
              value={formData.label}
              onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="e.g. Full Name"
            />
          </div>

          {/* Type */}
          <div className="space-y-1">
            <label className="text-sm font-semibold text-gray-700">Field Type</label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value as FieldType })}
              className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 outline-none bg-white"
            >
              {FIELD_TYPES.map(t => (
                <option key={t.type} value={t.type}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* Help Text / Question */}
          <div className="space-y-1">
            <label className="text-sm font-semibold text-gray-700">Question for AI to ask <span className="text-red-500">*</span></label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 outline-none min-h-[80px]"
              placeholder="e.g. Could you please tell me your full name?"
            />
            <p className="text-xs text-gray-500">The AI will use this as a guide when asking the user.</p>
          </div>

          {/* Required Checkbox */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="required-check"
              checked={formData.required}
              onChange={(e) => setFormData({ ...formData, required: e.target.checked })}
              className="w-5 h-5 text-primary-600 rounded focus:ring-primary-500 border-gray-300"
            />
            <label htmlFor="required-check" className="text-sm text-gray-700 font-medium select-none cursor-pointer">
              This field is required
            </label>
          </div>

          {/* Options Editor for Select Type */}
          {formData.type === 'select' && (
            <div className="space-y-3 pt-3 border-t border-gray-100">
              <label className="text-sm font-semibold text-gray-700">Dropdown Options</label>
              <div className="space-y-2">
                {formData.options?.map((opt, idx) => (
                  <div key={idx} className="flex gap-2">
                    <input
                      type="text"
                      value={opt.label}
                      onChange={(e) => updateOption(idx, 'label', e.target.value)}
                      placeholder="Label"
                      className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm"
                    />
                    <button onClick={() => removeOption(idx)} className="text-red-400 hover:text-red-600 p-2">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
                <button
                  onClick={addOption}
                  className="text-sm text-primary-600 font-medium flex items-center gap-1 hover:text-primary-700 mt-2"
                >
                  <Plus size={16} /> Add Option
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 font-medium hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!formData.label || !formData.description}
            className="px-6 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Save Field
          </button>
        </div>
      </div>
    </div>
  );
};
