import { useEffect } from 'react';

export default function FilterPanel({ 
  engineers, 
  projects, 
  selectedEngineer, 
  selectedProject,
  onEngineerChange,
  onProjectChange,
  onFetchData 
}) {
  useEffect(() => {
    onFetchData();
  }, [onFetchData]);

  const FilterChip = ({ active, onClick, children }) => (
    <button
      onClick={onClick}
      className={`filter-chip px-3 py-1.5 rounded-full text-sm border transition ${
        active 
          ? 'bg-accent-cyan/20 border-accent-cyan text-accent-cyan' 
          : 'bg-void-800 border-void-700 text-void-300 hover:border-void-500'
      }`}
    >
      {children}
    </button>
  );

  return (
    <div className="w-full max-w-3xl mx-auto mt-6">
      <div className="flex flex-wrap gap-4 justify-center">
        {/* Engineer filter */}
        <div className="flex items-center gap-2">
          <span className="text-void-500 text-sm">Engineer:</span>
          <div className="flex gap-2">
            <FilterChip 
              active={!selectedEngineer} 
              onClick={() => onEngineerChange(null)}
            >
              All
            </FilterChip>
            {engineers.map((eng) => (
              <FilterChip
                key={eng.username}
                active={selectedEngineer === eng.username}
                onClick={() => onEngineerChange(
                  selectedEngineer === eng.username ? null : eng.username
                )}
              >
                {eng.name.split(' ')[0]}
              </FilterChip>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="hidden sm:block w-px h-8 bg-void-700" />

        {/* Project filter */}
        <div className="flex items-center gap-2">
          <span className="text-void-500 text-sm">Project:</span>
          <div className="flex gap-2 flex-wrap">
            <FilterChip 
              active={!selectedProject} 
              onClick={() => onProjectChange(null)}
            >
              All
            </FilterChip>
            {projects.slice(0, 4).map((proj) => (
              <FilterChip
                key={proj.name}
                active={selectedProject === proj.name}
                onClick={() => onProjectChange(
                  selectedProject === proj.name ? null : proj.name
                )}
              >
                {proj.name}
              </FilterChip>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

