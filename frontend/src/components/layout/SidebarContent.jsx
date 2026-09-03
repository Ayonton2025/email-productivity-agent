import React from 'react'
import { ChevronRight, LogOut, Mail, User } from 'lucide-react'

const SidebarContent = ({
  navigationGroups,
  activeTab,
  setActiveTab,
  expandedGroups,
  setExpandedGroups,
  user,
  logout,
  onItemClick,
}) => {
  const [hoverGroup, setHoverGroup] = React.useState(null)
  const isTouch = React.useRef(false)

  // Detect touch device on mount
  React.useEffect(() => {
    isTouch.current = 'ontouchstart' in window || navigator.maxTouchPoints > 0
  }, [])

  const toggleGroup = (groupName) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupName]: !prev[groupName],
    }))
  }

  const handleGroupInteraction = (groupName) => {
    if (isTouch.current) {
      // On touch devices, click toggles
      toggleGroup(groupName)
    }
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 border-r border-slate-200 bg-white overflow-visible relative z-40">
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-visible">
        <div className="flex items-center flex-shrink-0 px-4">
          <Mail className="h-8 w-8 text-indigo-600" />
          <h1 className="ml-3 text-xl font-semibold text-slate-900">Bylix Email</h1>
        </div>

        {/* User Info */}
        {user && (
          <div className="px-4 py-3 border-b border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{user.full_name || user.email}</p>
                <p className="text-xs text-slate-500 truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        <nav className="mt-4 flex-1 px-3 space-y-1">
          {navigationGroups.map((group) => (
            <div
              key={group.name}
              className="space-y-1 relative"
              onMouseEnter={() => !isTouch.current && setHoverGroup(group.name)}
              onMouseLeave={() => setHoverGroup(null)}
            >
              {/* Group Header */}
              {group.items.length > 1 ? (
                <button
                  onClick={() => handleGroupInteraction(group.name)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors group/header"
                >
                  <span className="uppercase tracking-wider flex items-center gap-2">
                    {group.icon ? <group.icon className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    {group.name}
                  </span>
                  <ChevronRight
                    className={`h-4 w-4 transition-transform ${
                      (isTouch.current && expandedGroups[group.name]) || (!isTouch.current && hoverGroup === group.name)
                        ? 'rotate-90'
                        : ''
                    }`}
                  />
                </button>
              ) : (
                <div className="px-3 py-2 text-xs font-semibold text-slate-600 uppercase tracking-wider flex items-center gap-2">
                  {group.icon ? <group.icon className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  {group.name}
                </div>
              )}

              {/* Group Items */}
              {(group.items.length === 1 || (isTouch.current && expandedGroups[group.name])) && (
                <div className="space-y-1 ml-0">
                  {group.items.map((item) => {
                    const Icon = item.icon || Mail
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setActiveTab(item.id)
                          onItemClick?.()
                        }}
                        className={`group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg w-full text-left transition-colors ${
                          activeTab === item.id
                            ? 'bg-indigo-600 text-white'
                            : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                        }`}
                      >
                        <Icon
                          className={`flex-shrink-0 h-5 w-5 mr-3 ${
                            activeTab === item.id ? 'text-white' : 'text-slate-500'
                          }`}
                        />
                        {item.name}
                      </button>
                    )
                  })}
                </div>
              )}

              {/* Desktop fly-out submenu */}
              {!isTouch.current && group.items.length > 1 && hoverGroup === group.name && (
                <div className="absolute left-full top-0 ml-3 w-64 rounded-xl border border-slate-200 bg-white shadow-xl p-2 z-50 animate-flyoutIn">
                  <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    {group.name}
                  </div>
                  <div className="mt-1 space-y-1">
                    {group.items.map((item) => {
                      const Icon = item.icon || Mail
                      return (
                        <button
                          key={`${group.name}-${item.id}`}
                          type="button"
                          onClick={() => {
                            setActiveTab(item.id)
                            onItemClick?.()
                            setHoverGroup(null)
                          }}
                          className={`group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg w-full text-left transition-colors ${
                            activeTab === item.id
                              ? 'bg-indigo-600 text-white'
                              : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                          }`}
                        >
                          <Icon
                            className={`flex-shrink-0 h-5 w-5 mr-3 ${
                              activeTab === item.id ? 'text-white' : 'text-slate-500'
                            }`}
                          />
                          {item.name}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Logout Button */}
      {user && (
        <div className="flex-shrink-0 flex border-t border-slate-200 p-4">
          <button
            type="button"
            onClick={logout}
            className="flex-shrink-0 w-full group flex items-center px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <LogOut className="h-5 w-5 text-slate-500 group-hover:text-slate-700" />
            <span className="ml-3 text-sm font-medium">Sign out</span>
          </button>
        </div>
      )}
    </div>
  )
}

export default SidebarContent
