import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { listProjects, JiraProject } from "@/lib/api";

interface ProjectContextType {
  selectedProject:    string;
  setSelectedProject: (key: string) => void;
  projects:           JiraProject[];
  projectName:        string;
}

const ProjectContext = createContext<ProjectContextType>({
  selectedProject:    "BAI",
  setSelectedProject: () => {},
  projects:           [],
  projectName:        "Beko AI Sprint Management",
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [selectedProject, setSelectedProject] = useState<string>(
    () => (typeof window !== "undefined" ? localStorage.getItem("bai_selected_project") || "BAI" : "BAI")
  );
  const [projects, setProjects] = useState<JiraProject[]>([
    { key: "BAI", name: "Beko AI Sprint Management" },
  ]);

  useEffect(() => {
    listProjects().then((list) => {
      if (list.length > 0) setProjects(list);
    });
  }, []);

  const handleSelect = (key: string) => {
    setSelectedProject(key);
    localStorage.setItem("bai_selected_project", key);
    window.dispatchEvent(new CustomEvent("bai:refresh"));
  };

  const projectName =
    projects.find((p) => p.key === selectedProject)?.name || selectedProject;

  return (
    <ProjectContext.Provider
      value={{ selectedProject, setSelectedProject: handleSelect, projects, projectName }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  return useContext(ProjectContext);
}
