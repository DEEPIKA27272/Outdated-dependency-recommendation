import os
import subprocess
import shutil
from bs4 import BeautifulSoup

# xample input GAVs to compare
old_gavs = [
    {'groupId': 'com.ibm.db2', 'artifactId': 'jcc', 'version': '11.5.5.0'}
    ]

new_gavs = [
        {'groupId': 'com.ibm.db2', 'artifactId': 'jcc', 'version': '11.5.9.0'}

]

# Report and dummy project folders
report_dir =r'C:\Users\deepi\Downloads\dummy\japireports'
minimal_project_dir = 'japi-runner'
os.makedirs(minimal_project_dir, exist_ok=True)

# JApiCmp POM template with full parameter setup
pom_template = """
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>japicmp-runner</artifactId>
    <version>1.0-SNAPSHOT</version>
    <build>
        <plugins>
            <plugin>
                <groupId>com.github.siom79.japicmp</groupId>
                <artifactId>japicmp-maven-plugin</artifactId>
                <version>0.18.3</version>
                <executions>
                    <execution>
                        <id>compare</id>
                        <goals>
                            <goal>cmp</goal>
                        </goals>
                        <phase>verify</phase>
                    </execution>
                </executions>
                <configuration>
                    <oldVersion>
                        <dependency>
                            <groupId>{old_group}</groupId>
                            <artifactId>{old_artifact}</artifactId>
                            <version>{old_version}</version>
                        </dependency>
                    </oldVersion>
                    <newVersion>
                        <dependency>
                            <groupId>{new_group}</groupId>
                            <artifactId>{new_artifact}</artifactId>
                            <version>{new_version}</version>
                        </dependency>
                    </newVersion>
                    <skipHtmlReport>false</skipHtmlReport>
                    <breakBuildOnBinaryIncompatibleModifications>false</breakBuildOnBinaryIncompatibleModifications>
                    <breakBuildOnSourceIncompatibleModifications>false</breakBuildOnSourceIncompatibleModifications>
                    <parameter>
                        <onlyModified>false</onlyModified>
                        <accessModifier>public</accessModifier>
                        <breakBuildOnBinaryIncompatibleModifications>false</breakBuildOnBinaryIncompatibleModifications>
                        <breakBuildOnSourceIncompatibleModifications>false</breakBuildOnSourceIncompatibleModifications>
                        <ignoreMissingClasses>true</ignoreMissingClasses>
                        <skipHtmlReport>false</skipHtmlReport>
                        <htmlTitle>JApiCmp Comparison - {old_artifact}</htmlTitle>
                    </parameter>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""

def check_breaking_changes(report_path):
    if not os.path.exists(report_path):
        print(f"Report not found: {report_path}")
        return False

    with open(report_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        breaking_changes = soup.find_all('td', string=lambda t: t and '(!)' in t)

    return len(breaking_changes) > 0

def run_japicmp_for_dependency(old_dep, new_dep, index):
    pom_content = pom_template.format(
        old_group=old_dep['groupId'],
        old_artifact=old_dep['artifactId'],
        old_version=old_dep['version'],
        new_group=new_dep['groupId'],
        new_artifact=new_dep['artifactId'],
        new_version=new_dep['version']
    )

    pom_path = os.path.join(minimal_project_dir, 'pom.xml')
    with open(pom_path, 'w') as f:
        f.write(pom_content)

    print(f" Running JApiCmp for {old_dep['artifactId']} ...")

    # Clean previous target folder
    target_dir = os.path.join(minimal_project_dir, 'target')
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    # Run Maven JApiCmp
    try:
        subprocess.run('mvn clean verify', cwd=minimal_project_dir, check=True, shell=True)
        print(" Maven build completed successfully.")
    except subprocess.CalledProcessError:
        print("Maven build failed. Skipping this dependency.")
        if os.path.exists(pom_path):
            os.remove(pom_path)
            print(f"🧹 Cleaned up pom.xml for {old_dep['artifactId']}.")
        return False

    # Copy generated report to unique filename
    source_report = os.path.join(minimal_project_dir, 'target', 'japicmp', 'compare.html')
    destination_report = os.path.join(report_dir, f'report_{index}_{old_dep["artifactId"]}.html')

    if os.path.exists(source_report):
        shutil.copyfile(source_report, destination_report)
        print(f" Report saved as: {destination_report}")
    else:
        print(f" Report not found for {old_dep['artifactId']}.")
        if os.path.exists(pom_path):
            os.remove(pom_path)
            print(f" Cleaned up pom.xml for {old_dep['artifactId']}.")
        return False

    # Check breaking changes
    breaking_changes_present = check_breaking_changes(destination_report)
    print(f" Breaking changes present for {old_dep['artifactId']}: {breaking_changes_present}")

    # Cleanup pom.xml after use
    if os.path.exists(pom_path):
        os.remove(pom_path)
        print(f" Cleaned up pom.xml for {old_dep['artifactId']}.")

    # Optional: Cleanup target folder (if you want)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
        print(f" Cleaned up target folder for {old_dep['artifactId']}.")

    return breaking_changes_present

# ✅ Run JApiCmp for all GAVs
breaking_changes_flags = []

for i, (old_gav, new_gav) in enumerate(zip(old_gavs, new_gavs)):
    flag = run_japicmp_for_dependency(old_gav, new_gav, i)
    breaking_changes_flags.append(flag)

print("\n All comparisons completed.")
print(f"Breaking changes flags: {breaking_changes_flags}")
print(f" Detailed reports are saved in the 'japicmp-reports' folder.")
