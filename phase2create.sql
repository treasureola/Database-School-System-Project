-- Active: 1682346338578@@phase2-7.cgi21eqy7g91.us-east-1.rds.amazonaws.com@3306@integration


use integration;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS students;
CREATE TABLE students (
	student_id int(8) NOT NULL,
	degree_id int(2) NOT NULL,
  semester varchar(6) NOT NULL,
  admit_year   INT(4) NOT NULL,
  PRIMARY KEY (student_id),
  FOREIGN KEY (student_id) REFERENCES user(user_id)
);

DROP TABLE IF EXISTS degrees;
CREATE TABLE degrees (
	degree_id int(2) not null,
	degree_name  varchar(50) not null,
  primary key(degree_id)
);


DROP TABLE IF EXISTS user_type;
CREATE TABLE user_type (
  id int(1) NOT NULL,
  name varchar(50) NOT NULL,
  primary key(id)
);

DROP TABLE IF EXISTS admitted;
CREATE TABLE admitted(
  a_id int(8),
  a_semester varchar(10),
  a_year year,
  accept varchar(30),
  fee varchar(5),
  congrats varchar(10),
  primary key(a_id,a_semester,a_year),
  foreign key(a_id) references user(user_id) ON DELETE CASCADE,
  foreign key(a_id,a_semester,a_year) references applications(student_id,semester,s_year) ON DELETE CASCADE
);

DROP TABLE IF EXISTS applications;
CREATE TABLE applications ( 
  status varchar(30), 
  student_id int(8),
  semester varchar(10),
  s_year year,
  degree_type varchar(10),
  prior_bac_deg_name varchar(10),
  prior_bac_deg_gpa float(4),
  prior_bac_deg_major varchar(20),
  prior_bac_deg_year varchar(4),
  prior_bac_deg_university varchar(20),
  GRE_verbal int(10),
  GRE_year year,
  GRE_quatitative int(10),
  GRE_advanced_score int(10),
  GRE_advanced_subject varchar(20),
  TOEFL_score int(10),
  TOEFL_date date,
  interest varchar(50),
  experience varchar(50),
  prior_ms_deg_name varchar(10),
  prior_ms_deg_gpa float(4),
  prior_ms_deg_major varchar(20),
  prior_ms_deg_year varchar(4),
  prior__deg_university varchar(20),
  s_date date,
  transcript varchar(30),
  student varchar(30),
  primary key(student_id,semester,s_year),
  foreign key(student_id) references user(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS Rapplications;
CREATE TABLE Rapplications ( 
  status varchar(30), 
  Rstudent_id int(8),
  Rsemester varchar(10),
  Rs_year year,
  Rdegree_type varchar(10),
  Rprior_bac_deg_name varchar(10),
  Rprior_bac_deg_gpa float(4),
  Rprior_bac_deg_major varchar(20),
  Rprior_bac_deg_year varchar(4),
  Rprior_bac_deg_university varchar(20),
  RGRE_verbal int(10),
  RGRE_year year,
  RGRE_quatitative int(10),
  RGRE_advanced_score int(10),
  RGRE_advanced_subject varchar(20),
  RTOEFL_score int(10),
  RTOEFL_date date,
  Rinterest varchar(50),
  Rexperience varchar(50),
  Rprior_ms_deg_name varchar(10),
  Rprior_ms_deg_gpa float(4),
  Rprior_ms_deg_major varchar(20),
  Rprior_ms_deg_year varchar(4),
  Rprior__deg_university varchar(20),
  Rs_date date,
  Rtranscript varchar(30),
  Rstudent varchar(30),
  primary key(Rstudent_id,Rsemester,Rs_year),
  foreign key(Rstudent_id) references user(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS faculty;
CREATE TABLE faculty (
  faculty_id      INT(8) NOT NULL,
  department      VARCHAR(50) NOT NULL,
  instructor      int(1),
  advisor         int(1),
  reviewr         int(1),
  PRIMARY KEY (faculty_id),
  FOREIGN KEY (faculty_id) REFERENCES user(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS review;
CREATE TABLE review (
  review_id int(8),
  student_id int(8),
  p_semester varchar(10),
  p_year year,
  rev_rating varchar (10),
  deficiency_course varchar(20),
  reason_reject varchar(20),
  GAS_comment varchar(100),
  decision varchar(30),
  recom_advisor varchar(30),
  status varchar(10),
  primary key(review_id,student_id,p_year,p_semester),
  foreign key(student_id) references user(user_id) ON DELETE CASCADE,
  foreign key(review_id) references user(user_id) ON DELETE CASCADE,
  foreign key(student_id,p_semester,p_year) references applications(student_id,semester,s_year) ON DELETE CASCADE
);


DROP TABLE IF EXISTS transcript;
CREATE TABLE transcript (
  t_id int(8),
  t_semester varchar(10),
  t_year year,
  school varchar(20),
  email varchar(20),
  contents varchar(600),
  decision varchar(10),
  primary key(t_id,t_semester,t_year),
  foreign key(t_id) references user(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS letter;
CREATE TABLE letter (
  user_id int(8),
  l_semester varchar(10),
  l_year year,
  letter_id int(5) AUTO_INCREMENT,
  recommenderName varchar(20),
  recommenderAffil varchar(20),
  recommenderEmail varchar(20),
  contents varchar(600),
  primary key(letter_id,user_id,l_semester,l_year),
  foreign key(user_id) references user(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS letter1;
CREATE TABLE letter1 (
  user_id int(8),
  l_semester varchar(10),
  l_year year,
  letter_id int(5) AUTO_INCREMENT,
  recommenderName1 varchar(20),
  recommenderAffil1 varchar(20),
  recommenderEmail1 varchar(20),
  contents varchar(600),
  primary key(letter_id,user_id,l_semester,l_year),
  foreign key(user_id) references user(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS letter2;
CREATE TABLE letter2 (
  user_id int(8),
  l_semester varchar(10),
  l_year year,
  letter_id int(5) AUTO_INCREMENT,
  recommenderName2 varchar(20),
  recommenderAffil2 varchar(20),
  recommenderEmail2 varchar(20),
  contents varchar(600),
  primary key(letter_id,user_id,l_semester,l_year),
  foreign key(user_id) references user(user_id) ON DELETE CASCADE
);


DROP TABLE IF EXISTS course;
CREATE TABLE course (
  id int(3) not null,
  dept_name varchar(50) not null,
	course_num int(8) not null,
	course_name varchar(50) not null,
	credit_hours int(5) not null,
  primary key(id)
);


DROP TABLE IF EXISTS user;
CREATE TABLE user (
	user_id int(8) NOT NULL UNIQUE,
	user_type int(1) NOT NULL,
	fname  varchar(50) NOT NULL, 
	lname varchar(50) NOT NULL,
  username varchar(50) NOT NULL,
	user_password varchar(50) NOT NULL, 
  user_address varchar(50) NOT NULL,
  user_phoneNUM varchar(50) NOT NULL,
  ssn varchar(50) not null,
	email varchar(50) not null,
  primary key(user_id),
  foreign key(user_type) references user_type(id)
);

DROP TABLE IF EXISTS student_courses;
CREATE TABLE student_courses ( 
	student_id int(8) NOT NULL,
	class_id   int(3) NOT NULL,
  grade  varchar(50) NOT NULL,
  csem   VARCHAR(50) NOT NULL,
  cyear  VARCHAR(4) NOT NULL,
  PRIMARY KEY (student_id, class_id, csem, cyear),
	FOREIGN KEY (student_id) REFERENCES user(user_id), 
 	FOREIGN KEY (class_id, csem, cyear) REFERENCES class_section(class_id, csem, cyear)
);

DROP TABLE IF EXISTS student_advisors;
CREATE TABLE student_advisors (
	studentID int(8) not NULL,
	advisorID int(8) not NULL,
  Primary Key (studentID),
	FOREIGN KEY (studentID) REFERENCES students(student_id),
 	FOREIGN KEY (advisorID) REFERENCES faculty(faculty_id)
);

DROP TABLE IF EXISTS alumni;
CREATE TABLE alumni (
	student_id int(8) NOT NULL,
	degree_id int(2) NOT NULL,
  semester varchar(6) NOT NULL,
	grad_year int(4) NOT NULL,
  PRIMARY KEY (student_id)
);

DROP TABLE IF EXISTS application;
CREATE TABLE application (
	gs_id  varchar(50) NOT NULL,
	app_status  varchar(50) NOT NULL,
	student_id int(8) NOT NULL,
	remarks varchar(50),
	FOREIGN KEY (student_id) REFERENCES user(user_id)
);

DROP TABLE IF EXISTS prerequisite;
CREATE TABLE prerequisite (
    course_id         INT(6) NOT NULL,
    prereq_type       ENUM("1", "2") NOT NULL,
    prereq_id         INT(6) NOT NULL,
    PRIMARY KEY(course_id, prereq_type),
    FOREIGN KEY (prereq_id) REFERENCES course(id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS class_section;
CREATE TABLE class_section (
    class_id            INT(6) NOT NULL,
    csem                VARCHAR(50) NOT NULL,
    cyear               VARCHAR(4) NOT NULL,
    day_of_week         ENUM('M', 'T', 'W', 'R', 'F') NOT NULL,
    class_time          VARCHAR(50) NOT NULL,
    course_id           INT(6) NOT NULL,
    faculty_id          INT(8) NOT NULL,
    PRIMARY KEY (class_id, csem, cyear),
    FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE
); 

DROP TABLE IF EXISTS graduation;
CREATE TABLE graduation (
	gs_id  int(8) NOT NULL,
	app_status  varchar(50) NOT NULL,
	student_id int(8) NOT NULL,
	remarks varchar(50),
	FOREIGN KEY (student_id) REFERENCES students(student_id),
  Foreign Key (gs_id) REFERENCES user(user_id)
);

DROP TABLE IF EXISTS phd_req;
CREATE TABLE phd_req (
	student_id int(8) NOT NULL,
	thesisapproved varchar(5) NOT NULL,
  Primary Key(student_id),
  Foreign Key (student_id) REFERENCES students(student_id)
);

DROP TABLE IF EXISTS applied_grad;
CREATE TABLE applied_grad (
	student_id int(8) NOT NULL,
	dtype int(2) NOT NULL,
  PRIMARY KEY (student_id)
);

DROP TABLE IF EXISTS need_advisor;
CREATE TABLE need_advisor (
	student_id int(8) NOT NULL
);


DROP TABLE IF EXISTS form1answer;
CREATE TABLE form1answer (
  student_id int(8) NOT NULL,
  courseID int(6) NOT NULL,
  Foreign Key (courseID) REFERENCES course(id)
);

DROP TABLE IF EXISTS student_status;
CREATE TABLE student_status (
	student_id int(8) NOT NULL,
  status varchar(50) NOT NULL,
  FOREIGN KEY (student_id) REFERENCES user(user_id)
);


SET FOREIGN_KEY_CHECKS=1;



insert into degrees values (20, 'MS Degree');
insert into degrees values (21, 'PhD Degree');

insert into user_type values (0, 'Systems Administrator');
insert into user_type values (1, 'Faculty');
insert into user_type values (2, 'Alumni');
insert into user_type values (3, 'Graduate Secretary');
insert into user_type values (4, 'MS Graduate Student');
insert into user_type values (5, 'PhD Student');
insert into user_type values (6, 'applicant');
insert into user_type values (7, 'CAC');

insert into course values (100, 'CSCI', 6221, 'SW Paradigms', 3);
insert into course values (101, 'CSCI', 6461, 'Computer Architecture', 3);
insert into course values (102, 'CSCI', 6212, 'Algorithms', 3);
insert into course values (103, 'CSCI', 6220, 'Machine Learning', 3);
insert into course values (104, 'CSCI', 6232, 'Networks 1', 3);
insert into course values (105, 'CSCI', 6233, 'Networks 2', 3);
insert into course values (106, 'CSCI', 6241, 'Databases 1', 3);
insert into course values (107, 'CSCI', 6242, 'Databases 2', 3);
insert into course values (108, 'CSCI', 6246, 'Compilers', 3);
insert into course values (109, 'CSCI', 6260, 'Multimedia', 3);
insert into course values (110, 'CSCI', 6251, 'Cloud Computing', 3);
insert into course values (111, 'CSCI', 6254, 'SW Engineering', 3);
insert into course values (112, 'CSCI', 6262, 'Graphics 1', 3);
insert into course values (113, 'CSCI', 6283, 'Security 1', 3);
insert into course values (114, 'CSCI', 6284, 'Cryptography', 3);
insert into course values (115, 'CSCI', 6286, 'Network Security', 3);
insert into course values (116, 'CSCI', 6325, 'Algorithms 2', 3);
insert into course values (117, 'CSCI', 6339, 'Embedded Systems', 3);
insert into course values (118, 'CSCI', 6384, 'Cryptography 2', 3);
insert into course values (119, 'ECE', 6241, 'Communication Theory', 3);
insert into course values (120, 'ECE', 6242, 'Information Theory', 2);
insert into course values (121, 'MATH', 6210, 'Logic', 2);

insert into user values (00000000, 0, 'Systems', 'Administrator', 'admin', 'pass', '2121 I St NW, Washington, DC 20052', '202-994-1000', '000-00-0000', 'admin@gwu.edu');
insert into user values (55555555, 4, 'Paul', 'McCartney', 'pcartney', 'tfaghk015', '2001 G St NW, Washington, DC 20052', '202-995-1001', '123-45-6789' , 'pcartney@gwu.edu');
insert into user values (66666666, 4, 'George', 'Harrison', 'gharrison', 'ptlhik990', '2003 K St NW, Washington, DC 20052', '202-959-1000', '987-32-3454', 'gharrison@gwu.edu');
insert into user values (99999999, 5, 'Ringo', 'Starr', 'rstarr', 'tplgik245', '2002 H St NW, Washington, DC 20052', '202-955-1000', '222-11-1111', 'rstarr@gwu.edu');
insert into user values (77777777, 2, 'Eric', 'Clapton', 'eclapton', 'jkjfd098', '2031 G St NW, Washington, DC 20052', '202-222-1000', '333-12-1232', 'eclapton@gwu.edu' );
insert into user values(33333333, 3, 'Emilia', 'Schmidt', 'semilia', 'jkoplkfd03', '1290 U St NW, Washington, DC 20052', '202-222-1000', '124-86-9834', 'semilia@gwu.edu');
insert into user values (11111111, 1, 'Bhagirath', 'Narahari', 'bhagi', 'jkjfd098', '2031 G St NW, Washington, DC 20052', '202-222-1000', '342-23-9233', 'bhagi@gwu.edu');
insert into user values (22222222, 1, 'Gabriel', 'Parmer', 'gparmer', 'uofd0932', '2033 L St NW, Washington, DC 20052', '202-222-1000', '231-34-2343', 'gparmer@gwu.edu' );
INSERT INTO user VALUES (12312312, 6, 'Lennon', 'John','ljohn', 'passes', '2003 H St NW, Washington, DC 20052', '443-888-9999', '111-19-111', 'ljohn@gwu.edu');
insert into user values (65656565, 6, 'Rayra', 'Starr', 'raystarr', 'tplgik2890', '2005 H St NW, Washington, DC 20052', '202-955-1020', '202-91-1131', 'raystarr@gwu.edu');
insert into user values (10101010, 7, 'Chairman', 'Chair', 'cac', 'passed', '2005 F St NW, Washington, DC 20052', '202-443-1100', '222-72-1110', 'cac@gwu.edu');

INSERT INTO applications VALUES ('review','12312312','Fall','2023','MS','','','','','','','','','','','','','','','','','','','','','','');
INSERT INTO applications VALUES ('incomplete','65656565','Spring','2024','','','','','','','','','','','','','','','','','','','','','','','');

insert into alumni values (77777777, 20, 'Spring', 2014);

insert into students values (55555555, 20, 'Spring', 2021);
insert into students values (66666666, 20, 'Fall' , 2021);
insert into students values (99999999, 21, 'Fall',  2021);

insert into phd_req values(99999999, 'False');

insert into faculty values (11111111, 'CSCI', 1, 1, 1);
insert into faculty values (22222222, 'CSCI', 1, 1, 0);
insert into faculty values (10101010, 'CSCI', 1, 1, 1);


insert into student_advisors values(55555555, 11111111);
insert into student_advisors values(66666666, 22222222);
insert into student_advisors values(99999999, 22222222);

-- FALL 2023 --
insert into class_section values(30, 'Fall', '2023', 'M', '15:00-17:30', 100, 11111111);
insert into class_section values(31, 'Fall', '2023', 'T', '15:00-17:30', 101, 11111111);
insert into class_section values(32, 'Fall', '2023', 'W', '15:00-17:30', 102, 11111111);
insert into class_section values(33, 'Fall', '2023', 'M', '18:00-20:30', 104, 11111111);
insert into class_section values(34, 'Fall', '2023', 'T', '18:00-20:30', 105, 11111111);
insert into class_section values(35, 'Fall', '2023', 'W', '18:00-20:30', 106, 11111111);
insert into class_section values(36, 'Fall', '2023', 'R', '18:00-20:30', 107, 11111111);
insert into class_section values(37, 'Fall', '2023', 'T', '15:00-17:30', 108, 11111111);
insert into class_section values(38, 'Fall', '2023', 'M', '18:00-20:30', 110, 11111111);
insert into class_section values(39, 'Fall', '2023', 'M', '15:30-18:00', 111, 11111111);
insert into class_section values(40, 'Fall', '2023', 'R', '18:00-20:30', 109, 11111111);
insert into class_section values(41, 'Fall', '2023', 'W', '18:00-20:30', 112, 11111111);
insert into class_section values(42, 'Fall', '2023', 'T', '18:00-20:30', 113, 11111111);
insert into class_section values(43, 'Fall', '2023', 'M', '18:00-20:30', 114, 11111111);
insert into class_section values(44, 'Fall', '2023', 'W', '18:00-20:30', 115, 11111111);
insert into class_section values(45, 'Fall', '2023', 'W', '15:00-17:30', 118, 11111111);
insert into class_section values(46, 'Fall', '2023', 'M', '18:00-20:30', 119, 11111111);
insert into class_section values(47, 'Fall', '2023', 'T', '18:00-20:30', 120, 11111111);
insert into class_section values(48, 'Fall', '2023', 'W', '18:00-20:30', 121, 11111111);
insert into class_section values(49, 'Fall', '2023', 'R', '16:00-18:30', 117, 11111111);

-- SPRING 2023 --
insert into class_section values(30, 'Spring', '2023', 'M', '15:00-17:30', 100, 11111111);
insert into class_section values(31, 'Spring', '2023', 'T', '15:00-17:30', 101, 11111111);
insert into class_section values(32, 'Spring', '2023', 'W', '15:00-17:30', 102, 11111111);
insert into class_section values(33, 'Spring', '2023', 'M', '18:00-20:30', 104, 11111111);
insert into class_section values(34, 'Spring', '2023', 'T', '18:00-20:30', 105, 11111111);
insert into class_section values(35, 'Spring', '2023', 'W', '18:00-20:30', 106, 11111111);
insert into class_section values(36, 'Spring', '2023', 'R', '18:00-20:30', 107, 11111111);
insert into class_section values(37, 'Spring', '2023', 'T', '15:00-17:30', 108, 11111111);
insert into class_section values(38, 'Spring', '2023', 'M', '18:00-20:30', 110, 11111111);
insert into class_section values(39, 'Spring', '2023', 'M', '15:30-18:00', 111, 11111111);
insert into class_section values(40, 'Spring', '2023', 'R', '18:00-20:30', 109, 11111111);
insert into class_section values(41, 'Spring', '2023', 'W', '18:00-20:30', 112, 11111111);
insert into class_section values(42, 'Spring', '2023', 'T', '18:00-20:30', 113, 11111111);
insert into class_section values(43, 'Spring', '2023', 'M', '18:00-20:30', 114, 11111111);
insert into class_section values(44, 'Spring', '2023', 'W', '18:00-20:30', 115, 11111111);
insert into class_section values(45, 'Spring', '2023', 'W', '15:00-17:30', 118, 11111111);
insert into class_section values(46, 'Spring', '2023', 'M', '18:00-20:30', 119, 11111111);
insert into class_section values(47, 'Spring', '2023', 'T', '18:00-20:30', 120, 11111111);
insert into class_section values(48, 'Spring', '2023', 'W', '18:00-20:30', 121, 11111111);
insert into class_section values(49, 'Spring', '2023', 'R', '16:00-18:30', 117, 11111111);

-- FALL 2022 --
insert into class_section values(30, 'Fall', '2022', 'M', '15:00-17:30', 100, 11111111);
insert into class_section values(31, 'Fall', '2022', 'T', '15:00-17:30', 101, 11111111);
insert into class_section values(32, 'Fall', '2022', 'W', '15:00-17:30', 102, 11111111);
insert into class_section values(33, 'Fall', '2022', 'M', '18:00-20:30', 104, 11111111);
insert into class_section values(34, 'Fall', '2022', 'T', '18:00-20:30', 105, 11111111);
insert into class_section values(35, 'Fall', '2022', 'W', '18:00-20:30', 106, 11111111);
insert into class_section values(36, 'Fall', '2022', 'R', '18:00-20:30', 107, 11111111);
insert into class_section values(37, 'Fall', '2022', 'T', '15:00-17:30', 108, 11111111);
insert into class_section values(38, 'Fall', '2022', 'M', '18:00-20:30', 110, 11111111);
insert into class_section values(39, 'Fall', '2022', 'M', '15:30-18:00', 111, 11111111);
insert into class_section values(40, 'Fall', '2022', 'R', '18:00-20:30', 109, 11111111);
insert into class_section values(41, 'Fall', '2022', 'W', '18:00-20:30', 112, 11111111);
insert into class_section values(42, 'Fall', '2022', 'T', '18:00-20:30', 113, 11111111);
insert into class_section values(43, 'Fall', '2022', 'M', '18:00-20:30', 114, 11111111);
insert into class_section values(44, 'Fall', '2022', 'W', '18:00-20:30', 115, 11111111);
insert into class_section values(45, 'Fall', '2022', 'W', '15:00-17:30', 118, 11111111);
insert into class_section values(46, 'Fall', '2022', 'M', '18:00-20:30', 119, 11111111);
insert into class_section values(47, 'Fall', '2022', 'T', '18:00-20:30', 120, 11111111);
insert into class_section values(48, 'Fall', '2022', 'W', '18:00-20:30', 121, 11111111);
insert into class_section values(49, 'Fall', '2022', 'R', '16:00-18:30', 117, 11111111);

-- SPRING 2022 --
insert into class_section values(30, 'Spring', '2022', 'M', '15:00-17:30', 100, 11111111);
insert into class_section values(31, 'Spring', '2022', 'T', '15:00-17:30', 101, 11111111);
insert into class_section values(32, 'Spring', '2022', 'W', '15:00-17:30', 102, 11111111);
insert into class_section values(33, 'Spring', '2022', 'M', '18:00-20:30', 104, 11111111);
insert into class_section values(34, 'Spring', '2022', 'T', '18:00-20:30', 105, 11111111);
insert into class_section values(35, 'Spring', '2022', 'W', '18:00-20:30', 106, 11111111);
insert into class_section values(36, 'Spring', '2022', 'R', '18:00-20:30', 107, 11111111);
insert into class_section values(37, 'Spring', '2022', 'T', '15:00-17:30', 108, 11111111);
insert into class_section values(38, 'Spring', '2022', 'M', '18:00-20:30', 110, 11111111);
insert into class_section values(39, 'Spring', '2022', 'M', '15:30-18:00', 111, 11111111);
insert into class_section values(40, 'Spring', '2022', 'R', '18:00-20:30', 109, 11111111);
insert into class_section values(41, 'Spring', '2022', 'W', '18:00-20:30', 112, 11111111);
insert into class_section values(42, 'Spring', '2022', 'T', '18:00-20:30', 113, 11111111);
insert into class_section values(43, 'Spring', '2022', 'M', '18:00-20:30', 114, 11111111);
insert into class_section values(44, 'Spring', '2022', 'W', '18:00-20:30', 115, 11111111);
insert into class_section values(45, 'Spring', '2022', 'W', '15:00-17:30', 118, 11111111);
insert into class_section values(46, 'Spring', '2022', 'M', '18:00-20:30', 119, 11111111);
insert into class_section values(47, 'Spring', '2022', 'T', '18:00-20:30', 120, 11111111);
insert into class_section values(48, 'Spring', '2022', 'W', '18:00-20:30', 121, 11111111);
insert into class_section values(49, 'Spring', '2022', 'R', '16:00-18:30', 117, 11111111);



-- STUDENT TRANSCRIPTS --

-- SW Engineering --
insert into student_courses values(55555555, 39, 'B', 'Spring','2023'); 
-- Graphics 1 --
insert into student_courses values(55555555, 41, 'F', 'Spring','2023'); 
-- Multimedia --
insert into student_courses values(55555555, 42, 'B', 'Spring','2023'); 
-- Security 1 --
insert into student_courses values(55555555, 40, 'B', 'Spring','2023'); 

-- SW Paradigms --
insert into student_courses values(55555555, 30, 'A', 'Fall', '2022');
-- Algorithms --
insert into student_courses values(55555555, 32, 'A', 'Fall', '2022');
-- Computer Architecture --
insert into student_courses values(55555555, 31, 'A', 'Fall', '2022');
-- Networks 1 --
insert into student_courses values(55555555, 33, 'A', 'Fall', '2022'); 


insert into student_courses values(66666666, 47, 'C', 'Fall', '2022');
insert into student_courses values(66666666, 30, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 31, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 32, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 33, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 34, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 35, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 36, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 42, 'B', 'Fall', '2022');
insert into student_courses values(66666666, 43, 'B', 'Fall', '2022');

insert into student_courses values(99999999, 30, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 32, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 34, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 35, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 36, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 38, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 39, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 41, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 44, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 49, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 48, 'A', 'Fall', '2022');
insert into student_courses values(99999999, 37, 'A', 'Fall', '2022');

insert into student_courses values(77777777, 30, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 32, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 31, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 33, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 34, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 35, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 36, 'B', 'Fall', '2022');
insert into student_courses values(77777777, 42, 'A', 'Fall', '2022');
insert into student_courses values(77777777, 43, 'A', 'Fall', '2022');
insert into student_courses values(77777777, 44, 'A', 'Fall', '2022');


INSERT INTO prerequisite VALUES (105, "1", 104);
INSERT INTO prerequisite VALUES (107, "1", 106);
INSERT INTO prerequisite VALUES (108, "1", 101);
INSERT INTO prerequisite VALUES (108, "2", 102);
INSERT INTO prerequisite VALUES (110, "1", 101);
INSERT INTO prerequisite VALUES (111, "1", 100);
INSERT INTO prerequisite VALUES (113, "1", 102);
INSERT INTO prerequisite VALUES (114, "1", 102);
INSERT INTO prerequisite VALUES (115, "1", 113);
INSERT INTO prerequisite VALUES (115, "2", 104);
INSERT INTO prerequisite VALUES (116, "1", 102);
INSERT INTO prerequisite VALUES (117, "1", 101);
INSERT INTO prerequisite VALUES (117, "2", 102);
INSERT INTO prerequisite VALUES (118, "1", 114);
