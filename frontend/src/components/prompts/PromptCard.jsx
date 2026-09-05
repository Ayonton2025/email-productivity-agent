import React from 'react'
import { CheckCircle } from 'lucide-react'

const PromptCard = ({
  prompt,
  categories,
  selected,
  getCategoryIcon,
  getCategoryColor,
  formatTemplatePreview,
  onSelect,
}) => {
  const CategoryIcon = getCategoryIcon(prompt.category)

  return (
    <div
      onClick={() => onSelect(prompt)}
      className={`p-4 cursor-pointer transition-colors ${selected ? 'bg-indigo-50 border-l-4 border-indigo-500' : 'hover:bg-gray-50'}`}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <CategoryIcon className={`h-4 w-4 ${getCategoryColor(prompt.category).split(' ')[1]}`} />
          <h3 className="font-semibold text-gray-900">{prompt.name}</h3>
        </div>
        <div className="flex items-center gap-1">
          {prompt.is_active && <CheckCircle className="h-4 w-4 text-green-500" />}
          {prompt.is_system && (
            <span className="inline-flex items-center px-2 py-1 rounded-full bg-orange-100 text-orange-800 text-xs">
              System
            </span>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-600 mb-2 line-clamp-2">{prompt.description || 'No description'}</p>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className={`inline-flex items-center px-2 py-1 rounded-full ${getCategoryColor(prompt.category)}`}>
          {categories.find((category) => category.id === prompt.category)?.name || prompt.category}
        </span>
        <span>v{prompt.version}</span>
      </div>
      <div className="mt-2 text-xs text-gray-400 font-mono">{formatTemplatePreview(prompt.template)}</div>
    </div>
  )
}

export default PromptCard
