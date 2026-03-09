**AI가 작성한 코드, 진짜 괜찮을까?**
**직접 측정 도구를 만들었습니다.**

2026년, GitHub 커밋의 약 4%가 AI가 작성한 코드입니다.
연말이면 20%에 도달할 전망이고요.

그런데 한 가지 의문이 들었습니다.

"우리 레포의 AI 코드 품질은 몇 점일까?"

이 질문에 답하는 도구가 없어서, 직접 만들었습니다.

---

**git-forensic** — Git 커밋 히스토리를 분석해서
AI가 작성한 코드의 품질을 자동으로 감사하는 CLI 도구입니다.

**동작 방식:**
커밋 메시지에서 Co-Authored-By, Generated-by 등의 시그널을 탐지하고,
각 커밋을 4가지 품질 차원으로 채점합니다.

- Commit Message (25%) — Conventional Commit 형식, 설명성
- Change Size (30%) — 집중된 변경 vs 과도한 리팩토링
- Test Coverage (30%) — 코드 변경에 테스트가 동반되었는지
- Documentation (15%) — 문서화 수준

결과는 터미널 리포트 또는 HTML 대시보드로 확인할 수 있습니다.

---

**기술 스택:**
- Python 3.11 + uv (패키지 관리)
- GitPython (커밋 파싱) + Rich (터미널 UI) + Click (CLI)
- 단일 파일 HTML 대시보드 (외부 라이브러리 제로)
- 외부 API 호출 없음 — 100% 로컬 실행

**실제 프로젝트 5개에 테스트한 결과:**
가장 흥미로웠던 발견은 "AI 코드의 품질 편차"였습니다.
커밋 메시지 품질은 평균 90점 이상으로 높았지만,
테스트 동반율은 평균 40점대로 일관되게 낮았습니다.

AI가 코드는 잘 짜지만, 테스트는 스스로 챙기지 않는다는 걸
수치로 확인한 셈입니다.

---

만들면서 중요하게 느낀 점:

AI 도구를 잘 쓰는 것도 중요하지만,
**"AI가 만든 결과물을 측정하고 판단하는 능력"**이
앞으로 개발자에게 더 중요해질 거라고 생각합니다.

측정할 수 없으면, 개선할 수도 없으니까요.

GitHub: https://github.com/hyunseung1119/forensic
설치: `pip install git+https://github.com/hyunseung1119/forensic.git`
실행: `git-forensic /path/to/repo`

피드백 환영합니다.

#ClaudeCode #AICodeQuality #GitForensic #DeveloperTools #Python #CLI
