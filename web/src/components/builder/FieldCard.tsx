import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { FormField } from '../../types/form';
import { GripVertical, Pencil, Trash2, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';

interface FieldCardProps {
  field: FormField;
  onEdit: (field: FormField) => void;
  onDelete: (id: string) => void;
}

export const FieldCard = ({ field, onEdit, onDelete }: FieldCardProps) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: field.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : 1,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={clsx(
        "bg-white border rounded-xl p-4 flex items-start gap-3 transition-all group",
        isDragging ? "shadow-lg border-primary-300 scale-[1.02]" : "shadow-sm border-gray-200 hover:border-gray-300"
      )}
    >
      <div 
        {...attributes} 
        {...listeners}
        className="mt-1 text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing"
      >
        <GripVertical size={20} />
      </div>

      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-gray-900">{field.label}</span>
          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200 font-mono">
            {field.type}
          </span>
          {field.required && (
            <span className="flex items-center gap-1 text-xs text-primary-600 font-medium px-2 py-0.5 bg-primary-50 rounded-full">
              <CheckCircle2 size={12} /> Required
            </span>
          )}
        </div>
        <p className="text-sm text-gray-600 line-clamp-1 italic">
          "{field.description}"
        </p>
      </div>

      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onEdit(field)}
          className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
          title="Edit"
        >
          <Pencil size={18} />
        </button>
        <button
          onClick={() => onDelete(field.id)}
          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Delete"
        >
          <Trash2 size={18} />
        </button>
      </div>
    </div>
  );
};
