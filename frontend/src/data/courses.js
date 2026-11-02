// Programmes offered at sign-up. Each one drives the suggestions shown after it is picked:
// specialisations, number of semesters, career goals and starter subjects.
export const COURSES = [
  {
    id: 'bca', label: 'BCA', full: 'Bachelor of Computer Applications', level: 'Undergraduate', semesters: 6, popular: true,
    specializations: ['Software Development', 'Data Analytics', 'Cloud Computing', 'Cyber Security', 'AI and Machine Learning'],
    careers: ['Software Developer', 'Web Developer', 'Data Analyst', 'Prepare for MCA'],
    subjects: ['Programming in C', 'Data Structures', 'Database Management', 'Operating Systems', 'Web Technologies', 'Mathematics'],
  },
  {
    id: 'mca', label: 'MCA', full: 'Master of Computer Applications', level: 'Postgraduate', semesters: 4, popular: true,
    specializations: ['AI and Machine Learning', 'Data Science', 'Cloud Computing', 'Cyber Security', 'Full Stack Development'],
    careers: ['AI/ML Engineer', 'Data Scientist', 'Software Engineer', 'GenAI Developer'],
    subjects: ['Data Structures', 'Machine Learning', 'Operating Systems', 'Database Management', 'Design and Analysis of Algorithms', 'Mathematics'],
  },
  {
    id: 'btech-cse', label: 'B.Tech CSE', full: 'B.Tech Computer Science and Engineering', level: 'Undergraduate', semesters: 8, popular: true,
    specializations: ['AI and Machine Learning', 'Data Science', 'Cyber Security', 'Cloud Computing', 'Full Stack Development'],
    careers: ['Software Engineer', 'Data Scientist', 'Machine Learning Engineer', 'Higher studies (M.Tech / MS)'],
    subjects: ['Data Structures', 'Operating Systems', 'Computer Networks', 'Database Management', 'Machine Learning', 'Mathematics'],
  },
  {
    id: 'btech-it', label: 'B.Tech IT', full: 'B.Tech Information Technology', level: 'Undergraduate', semesters: 8,
    specializations: ['Cloud Computing', 'Cyber Security', 'Data Analytics', 'Software Engineering'],
    careers: ['Software Engineer', 'Cloud Engineer', 'Security Analyst'],
    subjects: ['Data Structures', 'Operating Systems', 'Computer Networks', 'Database Management', 'Mathematics'],
  },
  {
    id: 'bsc-it', label: 'B.Sc IT / CS', full: 'B.Sc Information Technology / Computer Science', level: 'Undergraduate', semesters: 6,
    specializations: ['Software Development', 'Data Science', 'Networking'],
    careers: ['Software Developer', 'IT Support Engineer', 'Prepare for MCA / M.Sc'],
    subjects: ['Programming in C', 'Data Structures', 'Database Management', 'Mathematics'],
  },
  {
    id: 'bba', label: 'BBA', full: 'Bachelor of Business Administration', level: 'Undergraduate', semesters: 6, popular: true,
    specializations: ['Marketing', 'Finance', 'Human Resources', 'Business Analytics', 'International Business'],
    careers: ['Management Trainee', 'Business Analyst', 'Marketing Executive', 'Prepare for MBA'],
    subjects: ['Principles of Management', 'Financial Accounting', 'Marketing Management', 'Business Statistics', 'Business Economics'],
  },
  {
    id: 'mba', label: 'MBA', full: 'Master of Business Administration', level: 'Postgraduate', semesters: 4, popular: true,
    specializations: ['Marketing', 'Finance', 'Human Resources', 'Business Analytics', 'Operations'],
    careers: ['Business Analyst', 'Product Manager', 'Financial Analyst', 'Consultant'],
    subjects: ['Managerial Economics', 'Corporate Finance', 'Marketing Management', 'Business Analytics', 'Organisational Behaviour'],
  },
  {
    id: 'bcom', label: 'B.Com', full: 'Bachelor of Commerce', level: 'Undergraduate', semesters: 6,
    specializations: ['Accounting and Taxation', 'Banking and Finance', 'Computer Applications'],
    careers: ['Accountant', 'Chartered Accountant (CA)', 'Banking', 'Prepare for MBA'],
    subjects: ['Financial Accounting', 'Business Law', 'Cost Accounting', 'Business Statistics'],
  },
  {
    id: 'mtech-cse', label: 'M.Tech CSE', full: 'M.Tech Computer Science and Engineering', level: 'Postgraduate', semesters: 4,
    specializations: ['AI and Machine Learning', 'Data Science', 'Cyber Security', 'Software Engineering'],
    careers: ['Research Engineer', 'Machine Learning Engineer', 'Lecturer', 'PhD'],
    subjects: ['Advanced Algorithms', 'Machine Learning', 'Research Methodology', 'Operating Systems'],
  },
  {
    id: 'msc-ds', label: 'M.Sc Data Science', full: 'M.Sc Data Science / Computer Science', level: 'Postgraduate', semesters: 4,
    specializations: ['Data Science', 'AI and Machine Learning', 'Big Data'],
    careers: ['Data Scientist', 'Data Engineer', 'Research Associate'],
    subjects: ['Statistics', 'Machine Learning', 'Data Structures', 'Database Management', 'Mathematics'],
  },
];

export const OTHER_COURSE = {
  id: 'other', label: 'Other', full: 'Another programme', level: 'Other', semesters: 8,
  specializations: [], careers: ['Prepare for exams', 'Build a strong foundation'],
  subjects: ['Mathematics'],
};

export const LEARNING_STYLES = [
  { value: 'Visual', hint: 'diagrams and examples' },
  { value: 'Reading/Writing', hint: 'notes and summaries' },
  { value: 'Practice-based', hint: 'problems and quizzes' },
  { value: 'Mixed', hint: 'a bit of everything' },
];

export function searchCourses(query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return COURSES.filter((c) => c.label.toLowerCase().includes(q) || c.full.toLowerCase().includes(q)
    || c.id.includes(q.replace(/[^a-z]/g, ''))).slice(0, 6);
}
