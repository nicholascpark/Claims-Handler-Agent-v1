import { useState } from 'react';
import { useFormBuilderStore } from '../../stores/formBuilderStore';
import { ArrowLeft, ArrowRight, Plus } from 'lucide-react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { FieldCard } from './FieldCard';
import { FieldEditor } from './FieldEditor';
import { FormField } from '../../types/form';

export const FieldsStep = () => {
  const { config, addField, updateField, removeField, reorderFields, nextStep, prevStep } = useFormBuilderStore();
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingField, setEditingField] = useState<FormField | undefined>(undefined);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = config.fields.findIndex((f) => f.id === active.id);
      const newIndex = config.fields.findIndex((f) => f.id === over?.id);
      reorderFields(arrayMove(config.fields, oldIndex, newIndex));
    }
  };

  const openAddModal = () => {
    setEditingField(undefined);
    setIsEditorOpen(true);
  };

  const openEditModal = (field: FormField) => {
    setEditingField(field);
    setIsEditorOpen(true);
  };

  const handleSaveField = (field: FormField) => {
    if (editingField) {
      updateField(field.id, field);
    } else {
      addField(field);
    }
  };

  const requiredCount = config.fields.filter(f => f.required).length;
  const optionalCount = config.fields.length - requiredCount;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">What information do you need?</h2>
        <p className="text-gray-500 mt-2">The AI will collect this information during the conversation.</p>
      </div>

      <div className="space-y-4">
        {config.fields.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-2xl bg-gray-50">
            <p className="text-gray-500 mb-4">No fields added yet.</p>
            <button
              onClick={openAddModal}
              className="inline-flex items-center gap-2 text-primary-600 font-medium hover:text-primary-700"
            >
              <Plus size={20} /> Add your first field
            </button>
          </div>
        ) : (
          <div className="bg-gray-50/50 p-1 rounded-xl">
             <div className="text-xs text-center text-gray-400 py-2 mb-2 flex items-center justify-center gap-2">
                <span>💡 Drag cards to reorder the conversation flow</span>
             </div>
             
             <DndContext 
                sensors={sensors} 
                collisionDetection={closestCenter} 
                onDragEnd={handleDragEnd}
              >
                <SortableContext 
                  items={config.fields.map(f => f.id)} 
                  strategy={verticalListSortingStrategy}
                >
                  <div className="space-y-3">
                    {config.fields.map((field) => (
                      <FieldCard 
                        key={field.id} 
                        field={field} 
                        onEdit={openEditModal} 
                        onDelete={removeField} 
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
          </div>
        )}

        <button
          onClick={openAddModal}
          className="w-full py-4 border-2 border-dashed border-gray-300 rounded-xl flex items-center justify-center gap-2 text-gray-500 font-medium hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50 transition-all group"
        >
          <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center group-hover:bg-primary-100 transition-colors">
            <Plus size={18} />
          </div>
          Add New Field
        </button>

        <div className="flex justify-center gap-6 text-sm text-gray-500 pt-2">
          <span>Required: <strong className="text-gray-900">{requiredCount}</strong></span>
          <span className="w-px h-4 bg-gray-300"></span>
          <span>Optional: <strong className="text-gray-900">{optionalCount}</strong></span>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <button
          onClick={prevStep}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 px-4 py-3 font-medium transition-colors"
        >
          <ArrowLeft size={18} />
          Back
        </button>
        <button
          onClick={nextStep}
          disabled={config.fields.length === 0}
          className="group flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-md hover:shadow-lg active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          Next: Preview
          <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>

      <FieldEditor 
        isOpen={isEditorOpen} 
        onClose={() => setIsEditorOpen(false)} 
        onSave={handleSaveField} 
        field={editingField}
      />
    </div>
  );
};
